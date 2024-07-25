import numpy as np
import tifffile as tiff

# Save bigtiff larger than 4gb to prove viability
shape = (200000, 10000)
# shape = (1000, 1000)
chunk_size = 100

data = np.memmap('large_matrix.dat', dtype='int8', mode='w+', shape=shape)

for i in range(shape[0]):
    data[i] = np.int8(np.random.rand(shape[1]) * 255)

with tiff.TiffWriter('large_matrix.tiff', bigtiff=True) as t:
    for i in range(0,shape[0], chunk_size):
        chunk = data[i:i+chunk_size]
        t.write(chunk, contiguous = True)

del data