from datetime import datetime
from . import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="cashier")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    min_stock_alert = db.Column(db.Integer, nullable=False, default=0)
    barcode = db.Column(db.String(32), unique=True, nullable=False)


class InventoryLog(db.Model):
    __tablename__ = "inventory_log"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    change_qty = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    total_purchases = db.Column(db.Float, default=0)


class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    balance = db.Column(db.Float, default=0)  # رصيد التاجر (له/عليه)


class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    total = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    net_total = db.Column(db.Float, default=0)
    cashier = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SupplierInvoice(db.Model):
    __tablename__ = "supplier_invoices"
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    total = db.Column(db.Float, default=0)
    paid = db.Column(db.Float, default=0)
    remaining = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SupplierInvoiceItem(db.Model):
    __tablename__ = "supplier_invoice_items"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("supplier_invoices.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(120), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(120), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)


class Return(db.Model):
    __tablename__ = "returns"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"))
    refund_total = db.Column(db.Float, default=0)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReturnItem(db.Model):
    __tablename__ = "return_items"
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey("returns.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(120), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    refund_amount = db.Column(db.Float, nullable=False)


class Shift(db.Model):
    __tablename__ = "shifts"
    id = db.Column(db.Integer, primary_key=True)
    cashier_name = db.Column(db.String(80), nullable=False)
    opening_cash = db.Column(db.Float, nullable=False, default=0)
    closing_cash = db.Column(db.Float, default=0)
    sales_total = db.Column(db.Float, default=0)
    net_cash = db.Column(db.Float, default=0)
    diff_cash = db.Column(db.Float, default=0)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(255))
