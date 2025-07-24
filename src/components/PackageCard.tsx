import React from 'react';

const PackageCard = ({
  pkg,
  owned,
  onBuy,
  onStart,
  completedTests,
  onTestSelect
}) => {
  // Show buy/start button or guide and test list
  if (!owned) {
    return (
      <div>
        <h2>{pkg.name}</h2>
        <p>{pkg.description}</p>
        <button onClick={onBuy}>Buy Package</button>
      </div>
    );
  }

  return (
    <div>
      <h2>{pkg.name}</h2>
      <p>{pkg.guideMessage}</p>
      <ul>
        {pkg.tests.map(test => (
          <li key={test.id}>
            <button
              onClick={() => onTestSelect(test.id)}
              disabled={completedTests.includes(test.id)}
            >
              {test.name} {completedTests.includes(test.id) ? '✅' : ''}
            </button>
          </li>
        ))}
      </ul>
      {completedTests.length === pkg.tests.length && (
        <div>All tests completed! 🎉</div>
      )}
    </div>
  );
};

export default PackageCard;
