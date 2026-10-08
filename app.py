import os
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_login import current_user
from config import config_dict, Config
from models import db, login_manager, csrf, limiter, mail


def create_app(config_name='default'):
    """Application factory for FreshMart Grocery."""
    app = Flask(__name__)
    app.config.from_object(config_dict.get(config_name, config_dict['default']))

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # User loader
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.shop import shop_bp
    from routes.cart import cart_bp
    from routes.orders import orders_bp
    from routes.payment import payment_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(admin_bp)

    # Global context processors for templates
    @app.context_processor
    def inject_global_data():
        from models import Category, Cart
        categories = []
        cart_count = 0
        try:
            categories = Category.query.order_by(Category.name.asc()).all()
            if current_user.is_authenticated:
                cart_items = Cart.query.filter_by(user_id=current_user.id).all()
                cart_count = sum(item.quantity for item in cart_items)
            else:
                guest_cart = session.get('guest_cart', {})
                cart_count = sum(guest_cart.values())
        except Exception:
            # Fallback if DB tables aren't created yet during initial boot
            pass

        return {
            'all_categories': categories,
            'cart_item_count': cart_count,
            'stripe_public_key': app.config.get('STRIPE_PUBLIC_KEY', ''),
            'currency_symbol': app.config.get('CURRENCY_SYMBOL', 'Rs.'),
            'free_delivery_threshold': app.config.get('FREE_DELIVERY_THRESHOLD', 1000.0),
            'standard_delivery_fee': app.config.get('STANDARD_DELIVERY_FEE', 100.0)
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('errors/429.html', error=e.description), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app


app = create_app(os.getenv('FLASK_ENV', 'development'))


def seed_database(app_instance):
    """Seed database with initial categories, sample products, coupons, and test accounts."""
    with app_instance.app_context():
        db.create_all()
        from models import User, Category, Product, Coupon

        # 1. Seed Categories
        categories_data = [
            {"name": "Vegetables", "description": "Farm-fresh organic and seasonal vegetables."},
            {"name": "Fruits", "description": "Handpicked juicy and nutritious fresh fruits."},
            {"name": "Dairy", "description": "Fresh milk, cheeses, butter, and fermented dairy products."},
            {"name": "Bakery", "description": "Artisan sourdough, breads, bagels, and fresh pastries."},
            {"name": "Beverages", "description": "Fresh squeezed juices, organic teas, specialty coffees."},
            {"name": "Snacks", "description": "Healthy roasted nuts, crisps, and whole grain treats."}
        ]

        category_map = {}
        for cat_info in categories_data:
            cat = Category.query.filter_by(name=cat_info['name']).first()
            if not cat:
                cat = Category(name=cat_info['name'], description=cat_info['description'])
                db.session.add(cat)
                db.session.flush()
            category_map[cat_info['name']] = cat

        # 2. Seed Products (at least 20 items across the 6 categories)
        products_data = [
            # Vegetables
            {
                "name": "Organic Red Tomatoes",
                "description": "Plump, sun-ripened organic vine tomatoes packed with rich antioxidants.",
                "price": 85.0,
                "stock_quantity": 60,
                "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=600&auto=format&fit=crop&q=80",
                "category": "Vegetables",
                "is_available": True
            },
            {
                "name": "Fresh Baby Spinach",
                "description": "Tender crisp baby spinach leaves, pre-washed and garden fresh.",
                "price": 60.0,
                "stock_quantity": 40,
                "image_url": "https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=600&auto=format&fit=crop&q=80",
                "category": "Vegetables",
                "is_available": True
            },
            {
                "name": "Himalayan Russet Potatoes (1kg)",
                "description": "Locally harvested firm russet potatoes, ideal for boiling, roasting, or baking.",
                "price": 55.0,
                "stock_quantity": 100,
                "image_url": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=600&auto=format&fit=crop&q=80",
                "category": "Vegetables",
                "is_available": True
            },
            {
                "name": "Crisp Orange Carrots (500g)",
                "description": "Sweet, crunchy and vitamin A rich farm-grown organic carrots.",
                "price": 50.0,
                "stock_quantity": 75,
                "image_url": "https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=600&auto=format&fit=crop&q=80",
                "category": "Vegetables",
                "is_available": True
            },
            {
                "name": "Crown Broccoli Florets",
                "description": "Vibrant dark green nutrient-rich broccoli heads from local farms.",
                "price": 95.0,
                "stock_quantity": 35,
                "image_url": "https://images.unsplash.com/photo-1584270354949-c26b0d5b4a0c?w=600&auto=format&fit=crop&q=80",
                "category": "Vegetables",
                "is_available": True
            },

            # Fruits
            {
                "name": "Royal Gala Red Apples (1kg)",
                "description": "Sweet, aromatic and crunchy mountain apples picked at peak maturity.",
                "price": 220.0,
                "stock_quantity": 50,
                "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=600&auto=format&fit=crop&q=80",
                "category": "Fruits",
                "is_available": True
            },
            {
                "name": "Fresh Organic Bananas (Dozen)",
                "description": "Naturally sweetened yellow bananas rich in potassium and healthy fiber.",
                "price": 120.0,
                "stock_quantity": 45,
                "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=600&auto=format&fit=crop&q=80",
                "category": "Fruits",
                "is_available": True
            },
            {
                "name": "Sweet Valencia Oranges (1kg)",
                "description": "Juicy, citrus-packed fresh oranges excellent for breakfast juices.",
                "price": 160.0,
                "stock_quantity": 40,
                "image_url": "https://images.unsplash.com/photo-1611080626919-7cf5a9dbab5b?w=600&auto=format&fit=crop&q=80",
                "category": "Fruits",
                "is_available": True
            },
            {
                "name": "Fresh Garden Strawberries (250g)",
                "description": "Fragrant and succulent red strawberries with intense natural sweetness.",
                "price": 190.0,
                "stock_quantity": 25,
                "image_url": "https://images.unsplash.com/photo-1464965911861-746a04b4bca6?w=600&auto=format&fit=crop&q=80",
                "category": "Fruits",
                "is_available": True
            },
            {
                "name": "Hass Creamy Avocados (2 pcs)",
                "description": "Perfect ripeness, buttery smooth Hass avocados for toast and salads.",
                "price": 280.0,
                "stock_quantity": 30,
                "image_url": "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=600&auto=format&fit=crop&q=80",
                "category": "Fruits",
                "is_available": True
            },

            # Dairy
            {
                "name": "Pasteurized Whole Milk (1L)",
                "description": "Pure, rich and creamy cow's milk from pasture-fed dairy herds.",
                "price": 95.0,
                "stock_quantity": 80,
                "image_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=600&auto=format&fit=crop&q=80",
                "category": "Dairy",
                "is_available": True
            },
            {
                "name": "Artisan Greek Yogurt (400g)",
                "description": "Thick, high-protein traditional strained plain Greek yogurt.",
                "price": 180.0,
                "stock_quantity": 30,
                "image_url": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&auto=format&fit=crop&q=80",
                "category": "Dairy",
                "is_available": True
            },
            {
                "name": "Aged Sharp Cheddar Cheese (200g)",
                "description": "Robust and creamy sharp cheddar cheese aged 12 months.",
                "price": 320.0,
                "stock_quantity": 25,
                "image_url": "https://images.unsplash.com/photo-1618164436241-4473940d1f5c?w=600&auto=format&fit=crop&q=80",
                "category": "Dairy",
                "is_available": True
            },
            {
                "name": "Farm Fresh Creamery Butter (250g)",
                "description": "Lightly salted golden churned butter made from pure whole milk cream.",
                "price": 210.0,
                "stock_quantity": 50,
                "image_url": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=600&auto=format&fit=crop&q=80",
                "category": "Dairy",
                "is_available": True
            },

            # Bakery
            {
                "name": "Artisan Sourdough Boule (500g)",
                "description": "Naturally fermented slow-rise sourdough bread with a crispy crust.",
                "price": 150.0,
                "stock_quantity": 20,
                "image_url": "https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=600&auto=format&fit=crop&q=80",
                "category": "Bakery",
                "is_available": True
            },
            {
                "name": "French Butter Croissants (Pack of 3)",
                "description": "Flaky, multi-layered golden croissants baked fresh daily with pure butter.",
                "price": 190.0,
                "stock_quantity": 18,
                "image_url": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&auto=format&fit=crop&q=80",
                "category": "Bakery",
                "is_available": True
            },
            {
                "name": "Multigrain Whole Wheat Loaf",
                "description": "Wholesome 100% whole grain loaf topped with toasted sesame and flax seeds.",
                "price": 110.0,
                "stock_quantity": 30,
                "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop&q=80",
                "category": "Bakery",
                "is_available": True
            },

            # Beverages
            {
                "name": "Cold-Pressed Fresh Orange Juice (500ml)",
                "description": "100% pure squeezed oranges with no added sugar or preservatives.",
                "price": 160.0,
                "stock_quantity": 40,
                "image_url": "https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=600&auto=format&fit=crop&q=80",
                "category": "Beverages",
                "is_available": True
            },
            {
                "name": "Organic Himalayan Green Tea (100g)",
                "description": "Handcrafted whole leaf green tea with soothing floral undertones.",
                "price": 250.0,
                "stock_quantity": 35,
                "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80",
                "category": "Beverages",
                "is_available": True
            },
            {
                "name": "Dark Roast Arabica Coffee Beans (250g)",
                "description": "Single-origin aromatic roasted coffee beans with chocolatey notes.",
                "price": 380.0,
                "stock_quantity": 28,
                "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&auto=format&fit=crop&q=80",
                "category": "Beverages",
                "is_available": True
            },

            # Snacks
            {
                "name": "Roasted California Almonds (200g)",
                "description": "Crunchy dry-roasted almonds lightly tossed in sea salt.",
                "price": 340.0,
                "stock_quantity": 45,
                "image_url": "https://images.unsplash.com/photo-1508061252445-5350f3ab0a55?w=600&auto=format&fit=crop&q=80",
                "category": "Snacks",
                "is_available": True
            },
            {
                "name": "Kettle Cooked Sea Salt Crisps (150g)",
                "description": "Extra crunchy hand-cooked potato chips with natural sea salt seasoning.",
                "price": 95.0,
                "stock_quantity": 55,
                "image_url": "https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=600&auto=format&fit=crop&q=80",
                "category": "Snacks",
                "is_available": True
            },
            {
                "name": "Belgian 70% Dark Chocolate Bar (100g)",
                "description": "Silky dark chocolate bar crafted with single-origin fair trade cocoa.",
                "price": 180.0,
                "stock_quantity": 40,
                "image_url": "https://images.unsplash.com/photo-1511381939415-e44015466834?w=600&auto=format&fit=crop&q=80",
                "category": "Snacks",
                "is_available": True
            }
        ]

        for p_data in products_data:
            existing_prod = Product.query.filter_by(name=p_data['name']).first()
            category_obj = category_map[p_data['category']]
            if not existing_prod:
                prod = Product(
                    name=p_data['name'],
                    description=p_data['description'],
                    price=p_data['price'],
                    stock_quantity=p_data['stock_quantity'],
                    image_url=p_data['image_url'],
                    category_id=category_obj.id,
                    is_available=p_data['is_available']
                )
                db.session.add(prod)

        # 3. Seed Users
        # Admin User
        admin_user = User.query.filter_by(email="admin@freshmart.com").first()
        if not admin_user:
            admin_user = User(
                full_name="FreshMart Administrator",
                email="admin@freshmart.com",
                phone="9800000001",
                role="admin",
                is_active=True
            )
            admin_user.set_password("Admin@1234")
            db.session.add(admin_user)

        # Customer User
        customer_user = User.query.filter_by(email="customer@freshmart.com").first()
        if not customer_user:
            customer_user = User(
                full_name="John Doe",
                email="customer@freshmart.com",
                phone="9841234567",
                role="customer",
                is_active=True
            )
            customer_user.set_password("Customer@1234")
            db.session.add(customer_user)

        # 4. Seed Promotional Coupons
        coupons_data = [
            {"code": "FRESH10", "discount_percent": 10.0, "discount_amount": 0.0, "min_order_amount": 300.0},
            {"code": "SAVE20", "discount_percent": 20.0, "discount_amount": 0.0, "min_order_amount": 800.0},
            {"code": "WELCOME50", "discount_percent": 0.0, "discount_amount": 50.0, "min_order_amount": 200.0}
        ]
        for c_data in coupons_data:
            existing_coupon = Coupon.query.filter_by(code=c_data['code']).first()
            if not existing_coupon:
                c = Coupon(
                    code=c_data['code'],
                    discount_percent=c_data['discount_percent'],
                    discount_amount=c_data['discount_amount'],
                    min_order_amount=c_data['min_order_amount'],
                    is_active=True
                )
                db.session.add(c)

        db.session.commit()
        print("FreshMart Grocery database successfully seeded.")


# Perform auto-seeding on application startup
try:
    seed_database(app)
except Exception as e:
    print(f"Database initialization info: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
