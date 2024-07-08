from ashlar import filepattern, reg 
import os

class Stitcher:
    def __init__(self, path, pattern, overlap, pixel_size):
        # self.metadata = FilePatternMetadata(path, pattern, overlap, pixel_size) #dont need bc reader defines its own metadata object?
        self.reader = filepattern.FilePatternReader(path, pattern, overlap, pixel_size) #in ashlar/filepattern.py pix_sz =1??
        self.edge_aligner = reg.EdgeAligner(self.reader,verbose=True)
        self.layer_aligner = reg.LayerAligner(self.reader, self.edge_aligner) #idk what reference_aligner is?? --- update - its edge aligner in ashlar.py?
        self.mosaics = []


    #this seems like a very stripped down version of what ashlar.py is doing... keeping it stripped down because im confused about everything else that is going on
    #in the script and it seems maybe not relevant to our usecase (using the FilePattern arg)
    def run(self):
        print("run")
        self.edge_aligner.run()
        print("edge aligner ran")
        self.mosaics.append(reg.Mosaic(self.edge_aligner, self.edge_aligner.shape, verbose = True))

        self.layer_aligner.run()
        self.mosaics.append(reg.Mosaic(self.layer_aligner, self.edge_aligner.mosaic_shape, verbose = True))

        writer_class = reg.PyramidWriter
        writer = writer_class(self.mosaics, "out.ome.tiff", verbose=True)
        writer.run()


    
if __name__ == "__main__":
    dir = os.getcwd()
    stitch = Stitcher("C:\\Users\\chloe\\wolkovich_s24\\TreeRings\\code\\image_stitch_testing\\ashlar\\20per_zoomout_correctdims\\focused_images", "frame_{row:01}_{col:01}_1.jpg", 0.20, 1.55)

    stitch.run()
