import React, { useEffect, useState } from "react";

const API_BASE = "http://retail-backend:5000";

function App() {
  const [products, setProducts] = useState([]);
  const [selectedQty, setSelectedQty] = useState({});
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [message, setMessage] = useState("");
  const [createdOrder, setCreatedOrder] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/products`)
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch(() => setMessage("Failed to load products"));
  }, []);

  const updateQty = (productId, qty) => {
    setSelectedQty((prev) => ({
      ...prev,
      [productId]: Number(qty)
    }));
  };

  const placeOrder = async () => {
    setMessage("");
    setCreatedOrder(null);

    const items = Object.entries(selectedQty)
      .filter(([_, qty]) => qty > 0)
      .map(([productId, qty]) => ({
        product_id: Number(productId),
        quantity: Number(qty)
      }));

    if (!customerName || !customerEmail || items.length === 0) {
      setMessage("Please enter customer details and select at least one product.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          customer_name: customerName,
          customer_email: customerEmail,
          items: items
        })
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.error || "Order creation failed");
        return;
      }

      setMessage("Order created successfully");
      setCreatedOrder(data);
      setSelectedQty({});
    } catch (error) {
      setMessage("Failed to create order");
    }
  };

  return (
    <div className="container">
      <h1>Retail Order Demo</h1>

      <div className="card">
        <h2>Customer Details</h2>
        <input
          type="text"
          placeholder="Customer Name"
          value={customerName}
          onChange={(e) => setCustomerName(e.target.value)}
        />
        <input
          type="email"
          placeholder="Customer Email"
          value={customerEmail}
          onChange={(e) => setCustomerEmail(e.target.value)}
        />
      </div>

      <div className="card">
        <h2>Products</h2>
        {products.length === 0 ? (
          <p>Loading products...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Price</th>
                <th>Stock</th>
                <th>Qty</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.name}</td>
                  <td>{p.category}</td>
                  <td>₹{p.price}</td>
                  <td>{p.stock_qty}</td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      value={selectedQty[p.id] || 0}
                      onChange={(e) => updateQty(p.id, e.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <button onClick={placeOrder}>Create Order</button>
      </div>

      {message && (
        <div className="card status">
          <strong>{message}</strong>
        </div>
      )}

      {createdOrder && (
        <div className="card">
          <h2>Order Result</h2>
          <p><strong>Order ID:</strong> {createdOrder.order_id}</p>
          <p><strong>Order Number:</strong> {createdOrder.order_number}</p>
          <p><strong>Total Amount:</strong> ₹{createdOrder.total_amount}</p>
          <p><strong>Status:</strong> {createdOrder.status}</p>
        </div>
      )}
    </div>
  );
}

export default App;