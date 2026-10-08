# 🥦 FreshMart - Modern Grocery Store Management Web Application

FreshMart is a complete, production-ready, full-stack web application for grocery store management and customer e-commerce. Built with Python (Flask framework), SQLite (via SQLAlchemy ORM), Stripe API test payments, Flask-Login authentication with bcrypt password hashing, and custom responsive CSS.

---

## 🚀 Key Features

### 👤 Customer Experience
1. **Interactive Registration (`register.html` + `validation.js`)**:
   - Field validation on blur (Full Name min 3 chars, valid email, 10-digit numeric phone, password complexity matching 1 uppercase, 1 lowercase, 1 number, 1 special symbol).
   - Password strength meter (Weak / Medium / Strong) with real-time feedback.
   - Show/hide password visibility toggle (eye icon).
   - Terms & conditions checkbox validation.
   - Green checkmark / red cross inline error indicators.
   - Server-side email uniqueness check and bcrypt password hashing.

2. **Secure Login (`login.html`)**:
   - Rate limiting via Flask-Limiter (5 attempts/minute).
   - Automatic 5-minute account lockout countdown after 5 consecutive failed attempts.
   - Generic error messages ("Invalid email or password") to prevent username enumeration.
   - Remember Me session cookie (30 days).
   - Google Sign-In button integration.

3. **Product Catalog & Live Search (`products.html` + `search.js`)**:
   - 20+ initial seeded products across 6 organic categories (Vegetables, Fruits, Dairy, Bakery, Beverages, Snacks).
   - Filter sidebar with multiple category selection, price range slider, and in-stock toggling.
   - Sort by Newest, Price (Low-High, High-Low), Name (A-Z, Z-A).
   - Instant live search dropdown with debounce.
   - Clean 10 items per page pagination.

4. **Dynamic Shopping Cart (`cart.html` + `cart.js`)**:
   - Real-time AJAX quantity increment/decrement with stock bounds.
   - Item removal with confirmation prompts.
   - Promotional coupon code engine (`FRESH10` for 10% off, `SAVE20` for 20% off, `WELCOME50` for Rs. 50 off).
   - Order summary calculation: Subtotal, Discount, Free delivery progress threshold (free above Rs. 1000).

5. **Stripe Checkout & Payments (`checkout.html` + `payment.js`)**:
   - Delivery address collection with option to save to user profile.
   - Stripe.js and Elements card input container (PCI-DSS compliant).
   - Automated stock inventory reduction upon successful payment.
   - Confirmation receipt with Stripe transaction ID.
   - Order confirmation email dispatch via Flask-Mail (with safe fallback logging).
   - Webhook endpoint (`/payment/webhook`) handling `payment_intent.succeeded` and `payment_intent.payment_failed`.

6. **Order History & Timeline Tracking (`orders.html` & `order_detail.html`)**:
   - Visual progression timeline: Placed → Paid → Shipped → Delivered.
   - Itemized line items with pricing and delivery address.
   - Customer cancellation option for unfulfilled orders with automatic restock.

### 🛡️ Admin Dashboard (`admin/dashboard.html` & routes)
- **Role-Protected**: Enforced with `@login_required` + `@admin_required` decorator.
- **Overview Metrics**: Total Revenue, Total Orders, Total Products, Total Registered Users.
- **Inventory Stock Alerts**: Automatic warning cards for products with stock ≤ 10 units.
- **Product Management**: Add new products (with image URL or file upload), edit details, and soft-delete/restore items.
- **Order Fulfillment**: Filter orders by status and update progression (pending → paid → shipped → delivered → cancelled).
- **User Management**: View all users, toggle account active/deactivate status.
- **Category Management**: Add, edit, and delete categories.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, Flask 3.0+
- **Database**: SQLite via SQLAlchemy ORM
- **Authentication**: Flask-Login + bcrypt (salt rounds = 12)
- **Security**: Flask-WTF CSRF protection, Flask-Limiter rate limiting, secure HTTPOnly cookies
- **Payments**: Stripe API SDK (Test Mode) + Stripe.js v3 Elements
- **Styling**: Pure custom Vanilla CSS (Mobile-first, Flexbox & CSS Grid, no Bootstrap or Tailwind)
- **Scripting**: Modular Vanilla JavaScript ES6+ (no inline scripts)

---

## 📦 Setup & Installation

### 1. Prerequisites
- Python 3.10+ installed
- Git (optional)

### 2. Navigate to Project Directory
```bash
cd groceryproj
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration (.env)
The project comes pre-configured with a `.env` file containing local development keys:
```env
SECRET_KEY=freshmart_grocery_super_secret_key_2026_production_grade
FLASK_ENV=development
DATABASE_URL=sqlite:///grocery.db
STRIPE_PUBLIC_KEY=pk_test_sample_grocery_key
STRIPE_SECRET_KEY=sk_test_sample_grocery_key
STRIPE_WEBHOOK_SECRET=whsec_sample_secret
```
*(You can replace `STRIPE_PUBLIC_KEY` and `STRIPE_SECRET_KEY` with your actual Stripe Dashboard test API keys at any time)*.

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

The database (`grocery.db`) and all required tables will be automatically created and populated on the first run.

---

## 🔑 Pre-seeded Demo Accounts

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@freshmart.com` | `Admin@1234` | Full access to `/admin` dashboard, product & order management |
| **Customer** | `customer@freshmart.com` | `Customer@1234` | Shopping, cart, checkout, profile & order history |

*(Or register any new customer account directly through `/auth/register`)*.

---

## 🎟️ Promotional Coupons

- `FRESH10` - 10% discount on orders over Rs. 300
- `SAVE20` - 20% discount on orders over Rs. 800
- `WELCOME50` - Rs. 50 off on orders over Rs. 200

---

## 🔒 Security Architecture
- **Password Protection**: Passwords hashed using standard `bcrypt` with salt rounds 12.
- **CSRF Protection**: Token validation on all POST requests via `Flask-WTF` (`meta[name="csrf-token"]` header for AJAX).
- **Rate Limiting**: IP-based rate limiting on login endpoint (5 attempts/minute) to stop brute-force attacks.
- **Lockout Mechanism**: Accounts are temporarily locked after 5 consecutive failed attempts.
- **SQL Injection Prevention**: SQLAlchemy parameterized queries used exclusively; no raw string concatenation.
- **XSS Prevention**: Automatic Jinja2 HTML escaping and sanitized data outputs.
