import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

print("All libraries imported successfully!")

# Simple Linear Regression
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 6, 8, 10])

model = LinearRegression()
model.fit(X, y)

print(f" Model trained! Coefficient: {model.coef_[0]}, Intercept: {model.intercept_}")

# Plot
plt.scatter(X, y, color='blue')
plt.plot(X, model.predict(X), color='red')
plt.title('Linear Regression Test')
plt.xlabel('X')
plt.ylabel('y')
plt.savefig('test_plot.png')
print("Plot saved as test_plot.png")