class TempSensor:
    """Class for temperature reading and writing"""
    def __init__(self, name=None, sensor_file=None, output_file=None, value=None):
        self.name = name
        self.sensor_file = sensor_file
        self.output_file = output_file
        self.value = value

    def display(self):
        print(str(self.name) + ': ' + str(self.value))

    def get_temp(self):
        temp_file = open(self.sensor_file)
        temp_value = temp_file.read()
        temp_file.close()
        self.value = float(temp_value)
        # temp_data = temp_value.split("\n")[1].split(" ")[9]
        # self.value = ((float(temp_data[2:])/1000) *1.8) + 32
        self.value = '{0:.1f}'.format((self.value))

    def get_out_file(self):
        temp_file = open(self.output_file)
        temp_value = temp_file.read()
        self.value = float(temp_value)
        temp_file.close()

    def write_temp_file(self):
        f = open(self.output_file, 'w')
        f.seek(0)
        f.truncate()
        f.write(str(self.value))
        f.flush()
        f.close()
