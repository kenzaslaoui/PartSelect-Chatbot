import { useState } from 'react'

function CompatibilityChecker() {
  const [partNumber, setPartNumber] = useState('')
  const [modelNumber, setModelNumber] = useState('')
  const [result, setResult] = useState(null)

  const checkCompatibility = async () => {
    // TODO: API call to check compatibility
  }

  return (
    <div className="compatibility-checker">
      <h2>Check Part Compatibility</h2>
      <input
        type="text"
        placeholder="Part Number"
        value={partNumber}
        onChange={(e) => setPartNumber(e.target.value)}
      />
      <input
        type="text"
        placeholder="Model Number"
        value={modelNumber}
        onChange={(e) => setModelNumber(e.target.value)}
      />
      <button onClick={checkCompatibility}>Check</button>
      {result && (
        <div className={`result ${result.compatible ? 'compatible' : 'incompatible'}`}>
          {result.message}
        </div>
      )}
    </div>
  )
}

export default CompatibilityChecker
