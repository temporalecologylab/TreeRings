# TreeRings

The TreeRings project is under development by students in the Temporal Ecology Lab at UBC. The project aims to create an open source and reproducible system to digitize ultra high resolution images of tree cookies. This is accomplished with a robot having control of a microscope camera that can navigate the X, Y, and Z directions. By systematically capturing images across the surface of the cookie, it is possible to stitch subframes of the cookie together into one large mosaic with the help of feature matching techniques. 

While this was designed to capture tree cookies, in theory this should also be able to be used to scan other planar objects such as planed mineral samples or pencil drawings. 

## Getting Started TODO

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites / Equipment

| Item | Description |
| ---  |     ---     | 
| FDM 3D Printer | Many components are 3D printed to allow for rapid prototyping. Printing quality varies across platforms and materials. Choose what is best for your lab - our parts were made with a Bambu Carbon X1 printer. |
| [Jetson Orin Nano](https://www.seeedstudio.com/NVIDIAr-Jetson-Orintm-Nano-Developer-Kit-p-5617.html?gad_source=1&gclid=Cj0KCQjww5u2BhDeARIsALBuLnM4tGqXsBM7JNxW5mwzGraFG74Qjp_JeM_HpbXGEc9Mlnl9b1s2fv8aAsPREALw_wcB) | This acts as the main computing device, running the GUI, stitching software, driving the camera, etc. |
| [OpenBuilds Acro](https://openbuilds.com/builds/openbuilds-acro-system.5416/) | The chassis for the gantry robot has already been designed and greatly documented by OpenBuilds. Building on top of this system has many benefits such as a library of documentation and customer service! |
| [OpenBuilds BlackBox X32](https://openbuildspartstore.com/BlackBox-Motion-Control-System-X32) | The motor controller to convert G-Code commands into electrical signals for the stepper motors. This was originally an Arduino - with a CNC hat and GRBL firmware. Sadly this quickly became a mess of wires and lacked the robust and clean wiring that the BlackBox has out of the box. |
| | | 

### Installing TODO

A step by step series of examples that tell you how to get a development env running

Say what the step will be

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests TODO

Explain how to run the automated tests for this system

### Break down into end to end tests TODO

Explain what these tests test and why

```
Give an example
```

### And coding style tests TODO 

Explain what these tests test and why

```
Give an example
```

## Deployment TODO

Add additional notes about how to deploy this on a live system

## Built With TODO

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing TODO

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning TODO 

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors TODO

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License TODO

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments TODO

* Hat tip to anyone whose code was used
* Inspiration
* etc

## Serpentine G-Code Control Logic
![Control Logic](./docs/diagrams/G_code_serpentine_logic.png)
![Live Demo](./docs/content/serpentine_example.gif)
