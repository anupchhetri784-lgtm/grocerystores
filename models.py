from datetime import datetime, timezone
import bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

# Extension singletons
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()


class User(db.Model, UserMixin):
    """User model for customers and store administrators."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='customer', nullable=False)  # 'customer' or 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Account lock out fields for failed login attempts
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Saved profile delivery address
    street_address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)

    # Relationships
    cart_items = db.relationship('Cart', backref='user', cascade='all, delete-orphan', lazy=True)
    orders = db.relationship('Order', backref='user', cascade='all, delete-orphan', lazy=True, order_by='desc(Order.created_at)')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_password(self, password: str) -> None:
        """Hash and save password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        self.password_hash = hashed.decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verify plain password against stored bcrypt hash."""
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False

    @property
    def is_admin(self) -> bool:
        """Helper to test admin role."""
        return self.role == 'admin'

    def is_locked(self) -> bool:
        """Check if user account is currently locked due to failed attempts."""
        if self.locked_until:
            now = datetime.now(timezone.utc)
            # Normalize to naive if needed
            lock_time = self.locked_until if self.locked_until.tzinfo else self.locked_until.replace(tzinfo=timezone.utc)
            return now < lock_time
        return False

    def get_remaining_lockout_seconds(self) -> int:
        """Calculate remaining lockout seconds for timer countdown."""
        if not self.locked_until:
            return 0
        now = datetime.now(timezone.utc)
        lock_time = self.locked_until if self.locked_until.tzinfo else self.locked_until.replace(tzinfo=timezone.utc)
        remaining = int((lock_time - now).total_seconds())
        return max(0, remaining)

    def __repr__(self):
        return f"<User {self.id}: {self.email} ({self.role})>"


class Category(db.Model):
    """Product category model."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # Relationship to products
    products = db.relationship('Product', backref='category', cascade='all, delete-orphan', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"


class Product(db.Model):
    """Grocery product model."""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    cart_items = db.relationship('Cart', backref='product', cascade='all, delete-orphan', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def is_in_stock(self) -> bool:
        """Check if product has stock and is marked available."""
        return self.is_available and (self.stock_quantity > 0)

    def to_dict(self):
        """Serialize product for AJAX live search and JSON responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock_quantity': self.stock_quantity,
            'image_url': self.image_url or '/static/images/placeholder.svg',
            'category_name': self.category.name if self.category else 'General',
            'category_id': self.category_id,
            'is_in_stock': self.is_in_stock,
            'is_available': self.is_available
        }

    def __repr__(self):
        return f"<Product {self.id}: {self.name} - Rs. {self.price}>"


class Cart(db.Model):
    """Shopping cart item model for persistent customer carts."""
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def subtotal(self) -> float:
        """Subtotal calculation for this cart item."""
        if self.product:
            return round(self.product.price * self.quantity, 2)
        return 0.0

    def __repr__(self):
        return f"<Cart User:{self.user_id} Product:{self.product_id} Qty:{self.quantity}>"


class Order(db.Model):
    """Customer order model."""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    # Available statuses: 'pending', 'paid', 'shipped', 'delivered', 'cancelled'
    stripe_payment_id = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    delivery_address = db.Column(db.Text, nullable=False)
    
    # Optional discount and delivery snapshot
    discount_amount = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    customer_notes = db.Column(db.Text, nullable=True)

    # Relationships
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def formatted_status(self) -> str:
        """Capitalized friendly status."""
        return self.status.capitalize()

    @property
    def total_items_count(self) -> int:
        """Total number of items in this order."""
        return sum(item.quantity for item in self.items)

    def __repr__(self):
        return f"<Order #{self.id} User:{self.user_id} Total:{self.total_amount} Status:{self.status}>"


class OrderItem(db.Model):
    """Individual line item in an Order."""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def subtotal(self) -> float:
        """Total price for this line item."""
        return round(self.unit_price * self.quantity, 2)

    def __repr__(self):
        return f"<OrderItem #{self.id} Order:{self.order_id} Product:{self.product_id} Qty:{self.quantity}>"


class Coupon(db.Model):
    """Promotional coupon discount model."""
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    min_order_amount = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def calculate_discount(self, subtotal: float) -> float:
        """Calculate discount amount for a given subtotal."""
        if not self.is_active or subtotal < self.min_order_amount:
            return 0.0
        if self.discount_percent > 0:
            return round((subtotal * self.discount_percent) / 100.0, 2)
        if self.discount_amount > 0:
            return min(self.discount_amount, subtotal)
        return 0.0

    def __repr__(self):
        return f"<Coupon {self.code}>"
