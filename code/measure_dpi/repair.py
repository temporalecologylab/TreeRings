import cv2

input_file = "21150please_2_corrupted.tiff"
output_file = "21150please_2.tiff"

img = cv2.imread(input_file, cv2.IMREAD_UNCHANGED)

if img is None:
    raise RuntimeError("OpenCV could not decode the image.")

print("Shape:", img.shape)
print("Dtype:", img.dtype)

cv2.imwrite(output_file, img)

print("Saved repaired TIFF:", output_file)