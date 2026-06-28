# Performance Optimization

For dense, high-frequency, or large-scale datasets, PyQtLabGraph provides several built-in mechanisms to maintain high rendering speeds and UI responsiveness:

---

## 1. Downsampling
Dynamically reduces the number of points drawn by grouping dense data points (activated via the Customize dialog or programmatically).

## 2. Clip to View
Avoids rendering calculations for data coordinates lying outside the current visible X range (activated via the Customize dialog).

## 3. Adaptive Rendering (Adaptive Performance)
When the number of visible raw data points in the viewport exceeds a high threshold (default: 5,000 points), PyQtLabGraph temporarily disables expensive styling details like antialiasing and markers to maintain smooth panning and zooming.

When you zoom back in and the point count falls below a lower threshold (default: 3,000 points), these detailed styling properties are automatically restored.

The visible point count is evaluated against the current X range before any logarithmic axis transform is applied. This keeps adaptive rendering behavior consistent for both linear and logarithmic X axes.
