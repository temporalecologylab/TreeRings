## Type

Practical Tools

## Title

Tree Imaging Machine: A Low Cost 

## Running Head (50 words)

## Abstract (350 words)

### Why did you do this project?

- digitizing cookies at high resolution
- introducing an affordable alternative to existing tools
- introducing a new scanning framework to potentially add new sensors such as IR cameras

### What did you do, and how?

- developed a robot which outputs scans of prepared increment tree cores and cross sections in ultra-high-resolution
- added a camera to a very common machine design: cartesian moving gantry machine
- built a GUI for an operator to interact with the robot
- developed software procedures to auto-focus images, collect overlapping images across the sample's surface area, and stitch the images into a mosaic

### What are the advantages of the method / apparatus?

- the machine frame can be made larger relatively affordably to account for long core samples
- batches of multiple samples can be set at once, allowing most of the running time of the robot to not need human intervention
- includes stitching on the device without the transferring images
- a configuration file allows the operator to adjust the DPI of output stitch

### How well does it work?

- the machine can stitch images over 20,000 DPI //Find exact value
- a theoretical maximum core length would be over a meter //Find exact value
- a maximum cookie cross section would be a few centimeters //find exact value

Digitizing samples for dendrochronology is a crucial step before analysis. Purpose built tools to scan increment cores are available but there is a gap for tools to scan cross-sections (cookies). Existing open-source tools have shown examples to capture images of the sample surface but still rely on professional image stitching software to prepare a final stitched mosaic. The Tree Imaging Machine (TIM) is an open-source robotic tool for acquiring scans of both increment cores and cookies at high-resolution (>20,000 DPI).

TIM is built on top of a common gantry machine design with movement in X, Y and Z axes. Using an attached microscope camera, TIM is able to capture images across the surface area of prepared samples. Images are automatically fed into an image stitching procedure to produce a single scan per sample, without the intervention of an operator. Moreover, multiple samples can be queued to be scanned sequentially. Cores up to 80 cm in length are able to be scanned in the standard TIM frame size but can be extended to over a meter by using a longer frame. The surface area of cookies can be scanned up to 13cm by 13cm (at 6300 DPI).

## Explain how your paper is suited to the journal's scope (50 words)

The Tree Imaging Machine (TIM) is a new open-source scanning tool for obtaining high-resolution scans of dendrochronological samples. TIM extends on the capabilities of the current tools in its class by scanning both increment cores and cross-sections, scanning batches of many samples sequentially, and performing image stitching without user intervention.


### Journal's Scope

- MEE focuses on developing and sharing new methods in ecology and evolution.
- Publishes work across many sub-disciplines in a unified forum.
- Emphasizes the description and analysis of new methods, rather than the results obtained using those methods.
- Accepts various types of papers:
    Full-length research articles
    Short descriptions of tools, hardware, or software
    Reviews
- Perspectives on methodological development
- Defines "methods" broadly—can be analytical, practical, or conceptual.
- A key goal is to maximize the adoption of new techniques by the research community.
- As of 6 July 2022, all submissions are published fully Open Access.
- Offers details on Open Access policy and fee waivers online.