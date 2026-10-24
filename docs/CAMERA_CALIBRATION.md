# Camera calibration

Three camera cards exist: Top Overview, Ground Coordinate, and Ground Inspection. None is labeled 360° because a panoramic lens was not identified.

`backend/app/vision/homography.py` solves a four-point homography. `rover_pose_from_pixel` returns `pose_valid: false` when fewer than four correspondences are available, when RMS reprojection error is above 2 px, or when the camera-to-rover offset is missing.

Suggested physical steps:

1. Print ArUco markers and record each marker's table coordinates in centimeters from the outside top-left corner.
2. Capture one still from the overview camera with the markers visible on the plywood plane.
3. Measure the offset from the detected tag frame to the rover center.
4. Store that offset in a local calibration file. Do not commit camera intrinsics you have not measured.

Until those steps happen, the dashboard reports homography invalid and does not draw a to-scale rover.
