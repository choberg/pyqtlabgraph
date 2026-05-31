# Performance Optimization

For dense, high-frequency, or large-scale datasets, PyQtLabGraph provides several built-in mechanisms to maintain high rendering speeds and UI responsiveness:

---

## 1. Downsampling
Dynamically reduces the number of points drawn by grouping dense data points (activated via the Customize dialog or programmatically).

## 2. Clip to View
Avoids rendering calculations for data coordinates lying outside the current visible X range (activated via the Customize dialog).

## 3. Adaptive Rendering (Adaptive Performance)
When the number of visible points in the viewport exceeds a high threshold (default: 20,000 points), PyQtLabGraph temporarily disables expensive styling details like antialiasing and markers to maintain smooth panning and zooming. 

When you zoom back in and the point count falls below a lower threshold (default: 10,000 points), these detailed styling properties are automatically restored.
