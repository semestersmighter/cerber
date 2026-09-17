function Button({ type = 'button', children, ...props }) {
  return (
    <button type={type} {...props}>
      {children}
    </button>
  )
}

export default Button
