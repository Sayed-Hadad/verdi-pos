let cart = [];
let allProducts = [];

// تحميل المنتجات عند التحميل
$(function() {
  loadAllProducts();
  $(document).keydown(function(e) {
    if (e.ctrlKey && e.key === 'p') {
      e.preventDefault();
      $("#pay-btn").click();
    }
    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault();
      $("#clear-btn").click();
    }
  });
});

function loadAllProducts() {
  $.get("/api/products/search?q=", function(res) {
    allProducts = res;
    renderProductsList(res);
  });
}

function renderProductsList(products) {
  const list = $("#products-list");
  list.empty();
  products.forEach((p) => {
    const isOutOfStock = p.stock_qty <= 0;
    const isLowStock = p.stock_qty > 0 && p.stock_qty <= (p.min_stock_alert || 5);
    const cardClass = isOutOfStock ? "out-of-stock" : isLowStock ? "low-stock" : "";
    const clickable = isOutOfStock ? "" : "onclick='addToCart(this, " + JSON.stringify(p).replace(/'/g, "\\'") + ")'";
    list.append(`
      <div class="product-card ${cardClass}" ${clickable}>
        <div class="name">${p.name}</div>
        <div class="price">${p.price.toFixed(2)} ج.م</div>
        <div class="stock">المخزون: ${p.stock_qty}</div>
      </div>
    `);
  });
}

function addToCart(el, product) {
  if (product.stock_qty <= 0) return;
  const found = cart.find((c) => c.id === product.id);
  if (found) {
    if (found.qty < product.stock_qty) found.qty += 1;
  } else {
    cart.push({ id: product.id, name: product.name, price: product.price, qty: 1, max_stock: product.stock_qty });
  }
  renderCart();
}

function renderCart() {
  const tbody = $("#cart-body");
  tbody.empty();
  let subtotal = 0;
  let count = 0;
  cart.forEach((item, idx) => {
    const line = item.qty * item.price;
    subtotal += line;
    count += item.qty;
    tbody.append(`
      <tr>
        <td class="small">${item.name}</td>
        <td><input type="number" class="form-control form-control-sm" min="1" max="${item.max_stock}" value="${item.qty}" data-idx="${idx}" onchange="updateQty(${idx}, this.value)"></td>
        <td class="small">${item.price.toFixed(2)}</td>
        <td class="small fw-bold">${line.toFixed(2)}</td>
        <td><button class="btn btn-sm btn-outline-danger btn-sm" onclick="removeItem(${idx})">×</button></td>
      </tr>`);
  });
  $("#subtotal").text(subtotal.toFixed(2));
  $("#cart-count").text(count);
  recalcTotal();
}

function updateQty(idx, val) {
  const max = cart[idx].max_stock;
  cart[idx].qty = Math.max(1, Math.min(parseInt(val || 1), max));
  renderCart();
}

function removeItem(idx) {
  cart.splice(idx, 1);
  renderCart();
}

function recalcTotal() {
  const subtotal = parseFloat($("#subtotal").text()) || 0;
  const discount = parseFloat($("#discount").val()) || 0;
  const tax = parseFloat($("#tax").val()) || 0;
  const total = subtotal - discount + tax;
  $("#total").text(total.toFixed(2));
}

$("#discount, #tax").on("input", recalcTotal);

$("#barcode-input").on("keypress", function(e) {
  if (e.which === 13) {
    e.preventDefault();
    searchProduct($(this).val());
    $(this).val("");
  }
});

$("#search-input").on("input", function() {
  const q = $(this).val().trim();
  if (q.length > 0) {
    const filtered = allProducts.filter((p) =>
      p.name.includes(q) || p.barcode.includes(q)
    );
    renderProductsList(filtered);
  } else {
    renderProductsList(allProducts);
  }
});

function searchProduct(q) {
  if (!q) return;
  $.get(`/api/products/search?q=${encodeURIComponent(q)}`, function(res) {
    if (res.length === 0) {
      alert("المنتج غير موجود");
      return;
    }
    const p = res[0];
    addToCart(null, p);
  });
}

$("#pay-btn").on("click", function() {
  if (cart.length === 0) {
    alert("السلة فارغة!");
    return;
  }
  const payload = {
    items: cart,
    discount: parseFloat($("#discount").val()) || 0,
    tax: parseFloat($("#tax").val()) || 0,
    customer_name: $("#customer-name").val(),
    customer_phone: $("#customer-phone").val(),
  };
  $.ajax({
    url: "/api/sale",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(payload),
    success: function(res) {
      window.location.href = `/invoice/${res.sale_id}`;
    },
    error: function(err) {
      alert("خطأ: " + (err.responseJSON?.error || "حدث خطأ في حفظ الفاتورة"));
    },
  });
});

$("#clear-btn").on("click", function() {
  if (confirm("هل تريد مسح السلة فعلاً؟")) {
    cart = [];
    $("#customer-name").val("");
    $("#customer-phone").val("");
    $("#discount").val(0);
    $("#tax").val(0);
    renderCart();
  }
});
