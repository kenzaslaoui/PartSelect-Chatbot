function ProductCard({ product }) {
  return (
    <div className="product-card">
      <h3>{product.name}</h3>
      <p className="part-number">Part #{product.part_number}</p>
      <p className="price">${product.price}</p>
      <p className="description">{product.description}</p>
      <button>View Details</button>
    </div>
  )
}

export default ProductCard
