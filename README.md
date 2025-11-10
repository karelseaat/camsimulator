 # GrblSimulator - A Graphical Interface for GRBL Simulation

GrblSimulator is a user-friendly graphical interface designed to simulate and visualize the operation of GRBL, an open-source CNC machine controller. The application allows users to manipulate the GRBL's position, speed, limits, and more in a visual, interactive manner, facilitating easier understanding and experimentation with the software.

## Features

- Visual representation of the simulated GRBL's current position and path
- Interactive control over the X, Y, and Z axes, including limit setting and movement
- Configurable feed rate for smooth motion control
- Real-time feedback on the current position, limits hit, and working state
- Alarm handling to prevent exceeding the machine's limits
- Built-in GRBL commands support
- Integrated status reporting for connected devices

## Installation

To use GrblSimulator, follow these steps:

1. Clone the repository: `git clone https://github.com/yourusername/GrblSimulator.git`
2. Navigate to the project directory: `cd GrblSimulator`
3. Run the application using Python: `python GrblSimulator.py`

## Usage

Upon launching, a graphical window will appear displaying the simulated GRBL's current position and limits on the X, Y, and Z axes. You can interact with the simulator by:

- Clicking and dragging the tool icon to move the GRBL along any axis
- Adjusting the limits of each axis using the limit buttons (min and max values)
- Changing the feed rate using the Feed Rate input field

In addition, you can send G-code commands to the simulator by entering them into the Command Input field and pressing Enter. The results will be displayed in the Output area.

## Dependencies

GrblSimulator requires Python 3.x to run. No additional dependencies are needed.

## Contributing

We welcome contributions to improve GrblSimulator! If you find any issues or have suggestions for new features, please open an issue on GitHub. Pull requests are also appreciated.

## License

GrblSimulator is released under the MIT License. See LICENSE for details.

## Credits

This project was created by [Your Name] as a tool to facilitate understanding and experimentation with GRBL simulation. Special thanks to the GRBL community for their open-source efforts that made this possible.