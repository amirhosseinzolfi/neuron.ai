import React, { useState } from 'react';
import PackageCard from './PackageCard';
import TestCard from './TestCard';

const SmartPackages = ({ packages, userPackages, onBuyPackage, onStartTest }) => {
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [activeTestId, setActiveTestId] = useState(null);
  const [completedTests, setCompletedTests] = useState([]);

  const handlePackageClick = (pkg) => {
    setSelectedPackage(pkg);
    setActiveTestId(null);
    setCompletedTests([]); // Optionally load from user progress
  };

  const handleBuy = (pkgId) => {
    onBuyPackage(pkgId);
    // ...existing code...
  };

  const handleStart = (pkg) => {
    // Show guide and list of tests
    // ...existing code...
  };

  const handleTestSelect = (testId) => {
    setActiveTestId(testId);
  };

  const handleTestFinish = (testId) => {
    setCompletedTests([...completedTests, testId]);
    setActiveTestId(null);
  };

  return (
    <div>
      {/* Smart package buttons */}
      <div>
        {packages.map(pkg => (
          <button key={pkg.id} onClick={() => handlePackageClick(pkg)}>
            {pkg.name}
          </button>
        ))}
      </div>
      {/* Show package card if selected */}
      {selectedPackage && !activeTestId && (
        <PackageCard
          pkg={selectedPackage}
          owned={userPackages.includes(selectedPackage.id)}
          onBuy={() => handleBuy(selectedPackage.id)}
          onStart={() => handleStart(selectedPackage)}
          completedTests={completedTests}
          onTestSelect={handleTestSelect}
        />
      )}
      {/* Show test card if a test is active */}
      {activeTestId && (
        <TestCard
          testId={activeTestId}
          onFinish={() => handleTestFinish(activeTestId)}
        />
      )}
    </div>
  );
};

export default SmartPackages;