from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    make_response,
)
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from .models import db, Product, InventoryLog, Customer, Sale, SaleItem, Shift, Setting, Supplier, SupplierInvoice, SupplierInvoiceItem, Return, ReturnItem
from .utils.barcode import generate_unique_code, generate_barcode_image, barcode_svg_base64
import os
import csv
import io

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    # إعادة التوجيه للـ POS مباشرة - الكاشير هي الصفحة الرئيسية
    return redirect(url_for("main.pos"))


@main_bp.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        name = request.form.get("name")
        price = float(request.form.get("price", 0))
        stock_qty = int(request.form.get("stock_qty", 0))
        min_stock_alert = int(request.form.get("min_stock_alert", 0))
        existing_codes = {p.barcode for p in Product.query.all()}
        code = generate_unique_code(existing_codes)
        generate_barcode_image(
            code, os.path.join("app", "static", "barcodes")
        )
        p = Product(
            name=name,
            price=price,
            stock_qty=stock_qty,
            min_stock_alert=min_stock_alert,
            barcode=code,
        )
        db.session.add(p)
        db.session.commit()
        flash("تم إضافة المنتج", "success")
        return redirect(url_for("main.products"))

    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("products.html", products=products)


@main_bp.route("/products/<int:pid>/update", methods=["POST"])
@login_required
def product_update(pid):
    product = Product.query.get_or_404(pid)
    product.name = request.form.get("name", product.name)
    product.price = float(request.form.get("price", product.price) or 0)
    product.stock_qty = int(request.form.get("stock_qty", product.stock_qty) or 0)
    product.min_stock_alert = int(request.form.get("min_stock_alert", product.min_stock_alert) or 0)
    db.session.commit()
    flash("تم تحديث المنتج", "success")
    return redirect(url_for("main.products"))


@main_bp.route("/products/<int:pid>/delete", methods=["POST"])
@login_required
def product_delete(pid):
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash("تم حذف المنتج", "success")
    return redirect(url_for("main.products"))


@main_bp.route("/print-barcodes")
@login_required
def print_barcodes():
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template("print_barcodes.html", products=products)


@main_bp.route("/inventory")
@login_required
def inventory():
    products = Product.query.order_by(Product.name.asc()).all()
    low = Product.query.filter(Product.stock_qty <= Product.min_stock_alert, Product.stock_qty > 0).all()
    zero = Product.query.filter(Product.stock_qty <= 0).all()
    return render_template(
        "inventory.html", products=products, low=low, zero=zero
    )


@main_bp.route("/pos")
@login_required
def pos():
    logo = Setting.query.get("logo_path")
    return render_template("pos.html", logo_path=logo.value if logo else "")


@main_bp.route("/api/products/search")
@login_required
def api_products_search():
    q = request.args.get("q", "").strip()
    results = (
        Product.query.filter(
            (Product.name.ilike(f"%{q}%")) | (Product.barcode.ilike(f"%{q}%"))
        )
        .limit(10)
        .all()
    )
    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "stock_qty": p.stock_qty,
                "barcode": p.barcode,
            }
            for p in results
        ]
    )


@main_bp.route("/api/sale", methods=["POST"])
@login_required
def api_sale():
    data = request.get_json(force=True)
    items = data.get("items", [])
    discount = float(data.get("discount", 0))
    tax = float(data.get("tax", 0))
    customer_name = data.get("customer_name")
    customer_phone = data.get("customer_phone")

    subtotal = sum(float(it["price"]) * int(it["qty"]) for it in items)
    net_total = subtotal - discount + tax

    customer = None
    if customer_name:
        customer = Customer.query.filter_by(name=customer_name).first()
        if not customer:
            customer = Customer(name=customer_name, phone=customer_phone)
            db.session.add(customer)
        customer.total_purchases = (customer.total_purchases or 0) + net_total

    sale = Sale(
        customer_id=customer.id if customer else None,
        total=subtotal,
        discount=discount,
        tax=tax,
        net_total=net_total,
        cashier=current_user.username,
    )
    db.session.add(sale)
    db.session.flush()

    for it in items:
        qty = int(it["qty"])
        price = float(it["price"])
        total = qty * price
        item = SaleItem(
            sale_id=sale.id,
            product_id=it.get("id"),
            product_name=it.get("name"),
            qty=qty,
            price=price,
            total=total,
        )
        db.session.add(item)
        if it.get("id"):
            product = Product.query.get(int(it["id"]))
            if product:
                product.stock_qty = max(0, product.stock_qty - qty)
    db.session.commit()

    return jsonify({"message": "تم حفظ الفاتورة", "sale_id": sale.id})


@main_bp.route("/invoice/<int:sale_id>")
@login_required
def invoice_view(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale_id).all()
    logo = Setting.query.get("logo_path")
    return render_template(
        "invoice.html",
        sale=sale,
        items=items,
        logo_path=logo.value if logo else "",
    )


@main_bp.route("/sales")
@login_required
def sales():
    sales_list = Sale.query.order_by(Sale.id.desc()).limit(50).all()
    return render_template("sales.html", sales=sales_list)


@main_bp.route("/api/sale/<int:sale_id>")
@login_required
def api_sale_details(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale_id).all()
    customer_name = ""
    if sale.customer_id:
        cust = Customer.query.get(sale.customer_id)
        customer_name = cust.name if cust else ""

    return jsonify({
        "id": sale.id,
        "customer": customer_name,
        "total": float(sale.net_total or sale.total or 0),
        "discount": float(sale.discount or 0),
        "tax": float(sale.tax or 0),
        "created_at": sale.created_at.strftime('%Y-%m-%d %H:%M'),
        "items": [
            {
                "product_id": it.product_id,
                "product_name": it.product_name,
                "qty": it.qty,
                "price": it.price,
                "total": it.total,
            }
            for it in items
        ],
    })


@main_bp.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        if name:
            c = Customer(name=name, phone=phone)
            db.session.add(c)
            db.session.commit()
            flash("تم إضافة العميل", "success")
        return redirect(url_for("main.customers"))
    customers = Customer.query.order_by(Customer.total_purchases.desc()).all()
    return render_template("customers.html", customers=customers)


@main_bp.route("/customers/export")
@login_required
def customers_export():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "phone", "total_purchases"])
    for c in customers:
        writer.writerow([
            c.id,
            c.name or "",
            c.phone or "",
            f"{(c.total_purchases or 0):.2f}",
        ])
    content = "\ufeff" + output.getvalue()  # BOM لضمان العربية في Excel
    resp = make_response(content)
    resp.headers["Content-Type"] = "application/vnd.ms-excel; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=customers.csv"
    return resp


@main_bp.route("/shifts", methods=["GET", "POST"])
@login_required
def shifts():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "open":
            shift = Shift(
                cashier_name=current_user.username,
                opening_cash=float(request.form.get("opening_cash", 0)),
            )
            db.session.add(shift)
            db.session.commit()
            flash("تم فتح الشيفت", "success")
        elif action == "close":
            shift_id = request.form.get("shift_id")
            shift = Shift.query.get(int(shift_id))
            if shift:
                shift.closing_cash = float(request.form.get("closing_cash", 0))
                shift.sales_total = float(request.form.get("sales_total", 0))
                shift.net_cash = shift.sales_total
                shift.diff_cash = shift.closing_cash - shift.opening_cash - shift.sales_total
                shift.end_time = datetime.utcnow()
                db.session.commit()
                flash("تم إغلاق الشيفت", "success")
        return redirect(url_for("main.shifts"))

    last_shifts = Shift.query.order_by(Shift.start_time.desc()).all()
    return render_template("shifts.html", shifts=last_shifts)


@main_bp.route("/reports")
@login_required
def reports():
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    def sum_period(start_date):
        return (
            db.session.query(db.func.sum(Sale.net_total))
            .filter(db.func.date(Sale.created_at) >= start_date)
            .scalar()
            or 0
        )

    data = {
        "daily": sum_period(today),
        "weekly": sum_period(week_ago),
        "monthly": sum_period(month_ago),
        "best": db.session.query(
            SaleItem.product_name, db.func.sum(SaleItem.qty).label("q")
        )
        .group_by(SaleItem.product_name)
        .order_by(db.desc("q"))
        .limit(5)
        .all(),
        "low_stock": Product.query.filter(
            Product.stock_qty <= Product.min_stock_alert
        ).all(),
        "shifts": Shift.query.order_by(Shift.start_time.desc()).limit(5).all(),
    }
    return render_template("reports.html", data=data)


@main_bp.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        if name:
            s = Supplier(name=name, phone=phone)
            db.session.add(s)
            db.session.commit()
            flash("تم إضافة التاجر", "success")
        return redirect(url_for("main.suppliers"))
    suppliers_list = Supplier.query.order_by(Supplier.id.desc()).all()
    return render_template("suppliers.html", suppliers=suppliers_list)


@main_bp.route("/suppliers/<int:sid>/update", methods=["POST"])
@login_required
def supplier_update(sid):
    supplier = Supplier.query.get_or_404(sid)
    supplier.name = request.form.get("name", supplier.name)
    supplier.phone = request.form.get("phone", supplier.phone)
    db.session.commit()
    flash("تم تحديث التاجر", "success")
    return redirect(url_for("main.suppliers"))


@main_bp.route("/suppliers/<int:sid>/delete", methods=["POST"])
@login_required
def supplier_delete(sid):
    supplier = Supplier.query.get_or_404(sid)
    invoices_count = SupplierInvoice.query.filter_by(supplier_id=sid).count()
    if invoices_count > 0:
        flash("لا يمكن الحذف لوجود فواتير مرتبطة", "danger")
        return redirect(url_for("main.suppliers"))
    db.session.delete(supplier)
    db.session.commit()
    flash("تم حذف التاجر", "success")
    return redirect(url_for("main.suppliers"))


@main_bp.route("/supplier-invoices", methods=["GET", "POST"])
@login_required
def supplier_invoices():
    products = Product.query.order_by(Product.name.asc()).all()
    suppliers_list = Supplier.query.order_by(Supplier.name.asc()).all()
    if request.method == "POST":
        supplier_id = int(request.form.get("supplier_id"))
        paid = float(request.form.get("paid", 0))
        items_json = request.form.get("items_json", "[]")
        import json

        try:
            items = json.loads(items_json)
        except Exception:
            items = []

        if not items:
            flash("أضف أصنافًا للفاتورة", "danger")
            return redirect(url_for("main.supplier_invoices"))

        total = 0
        invoice = SupplierInvoice(
            supplier_id=supplier_id,
            total=0,
            paid=paid,
            remaining=0,
        )
        db.session.add(invoice)
        db.session.flush()

        for it in items:
            pid = int(it.get("id")) if it.get("id") else None
            qty = int(it.get("qty", 0))
            cost = float(it.get("cost", 0))
            total_line = qty * cost
            total += total_line
            product = Product.query.get(pid) if pid else None
            name = product.name if product else it.get("name", "منتج")
            inv_item = SupplierInvoiceItem(
                invoice_id=invoice.id,
                product_id=pid,
                product_name=name,
                qty=qty,
                cost=cost,
                total=total_line,
            )
            db.session.add(inv_item)
            if product:
                product.stock_qty += qty

        invoice.total = total
        invoice.remaining = max(0, total - paid)

        supplier = Supplier.query.get(supplier_id)
        if supplier:
            supplier.balance += invoice.remaining

        db.session.commit()
        flash("تم تسجيل فاتورة المورد", "success")
        return redirect(url_for("main.supplier_invoices"))

    invoices = SupplierInvoice.query.order_by(SupplierInvoice.id.desc()).limit(20).all()
    supplier_map = {s.id: s.name for s in suppliers_list}
    return render_template(
        "supplier_invoices.html",
        products=products,
        suppliers=suppliers_list,
        invoices=invoices,
        supplier_map=supplier_map,
    )


@main_bp.route("/supplier-invoice/<int:invoice_id>")
@login_required
def supplier_invoice_view(invoice_id):
    invoice = SupplierInvoice.query.get_or_404(invoice_id)
    supplier = Supplier.query.get(invoice.supplier_id)
    items = SupplierInvoiceItem.query.filter_by(invoice_id=invoice_id).all()
    return render_template(
        "supplier_invoice_view.html",
        invoice=invoice,
        supplier=supplier,
        items=items,
    )


@main_bp.route("/returns", methods=["GET", "POST"])
@login_required
def returns():
    products = Product.query.order_by(Product.name.asc()).all()
    if request.method == "POST":
        items_json = request.form.get("items_json", "[]")
        note = request.form.get("note")
        import json
        try:
            items = json.loads(items_json)
        except Exception:
            items = []

        if not items:
            flash("أضف أصنافًا للمرتجع", "danger")
            return redirect(url_for("main.returns"))

        refund_total = 0
        ret = Return(refund_total=0, note=note)
        db.session.add(ret)
        db.session.flush()

        for it in items:
            pid = int(it.get("id")) if it.get("id") else None
            qty = int(it.get("qty", 0))
            refund_amount = float(it.get("refund", 0))
            refund_total += refund_amount
            product = Product.query.get(pid) if pid else None
            name = product.name if product else it.get("name", "منتج")
            ritem = ReturnItem(
                return_id=ret.id,
                product_id=pid,
                product_name=name,
                qty=qty,
                refund_amount=refund_amount,
            )
            db.session.add(ritem)
            if product:
                product.stock_qty += qty

        ret.refund_total = refund_total
        db.session.commit()
        flash("تم تسجيل المرتجع", "success")
        return redirect(url_for("main.returns"))

    recent_returns = Return.query.order_by(Return.id.desc()).limit(20).all()
    return render_template("returns.html", products=products, returns=recent_returns)


@main_bp.route("/api/barcode-image/<code>")
@login_required
def barcode_image(code):
    """Generate and return barcode as SVG (base64 encoded for inline display)"""
    try:
        img = barcode_svg_base64(code)
        return jsonify({"success": bool(img), "image": img})
    except Exception as e:
        return jsonify({"success": False, "image": "", "error": str(e)})


@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    logo_setting = Setting.query.get("logo_path")
    if request.method == "POST":
        logo_path = request.form.get("logo_path")
        if logo_setting:
            logo_setting.value = logo_path
        else:
            logo_setting = Setting(key="logo_path", value=logo_path)
            db.session.add(logo_setting)
        db.session.commit()
        flash("تم حفظ الإعدادات", "success")
        return redirect(url_for("main.settings"))
    return render_template("settings.html", logo_path=logo_setting.value if logo_setting else "")
