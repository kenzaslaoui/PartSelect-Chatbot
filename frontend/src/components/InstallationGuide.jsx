function InstallationGuide({ guide }) {
  return (
    <div className="installation-guide">
      <h2>Installation Guide</h2>
      <div className="metadata">
        <span>Difficulty: {guide?.difficulty}</span>
        <span>Time: {guide?.estimated_time}</span>
      </div>
      <div className="steps">
        {guide?.steps?.map((step, idx) => (
          <div key={idx} className="step">
            <span className="step-number">{idx + 1}</span>
            <p>{step}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default InstallationGuide
