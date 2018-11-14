# bioscreen
Python code to analyze and graph data from Bioscreen C growth experiments

### Introduction
The Bioscreen C machine allows for easy growth experiments with bacteria and yeast. An optical density reading is taken at several timepoints during the experiment, and ultimately, a growth curve figure is created. This module helps with summarizing and graphing data that come from these experiments, making figures like this one:

![Growth Curve Example](https://github.com/cwrussell/bioscreen/blob/master/example/data.LB.png)

### Quick Start Guide
After the experiment is completed, export the data as a '.csv' file. Then, in Python:

```
# import the module and create a new Experiment object
import bioscreen
expt = bioscreen.Experiment()

# set an experiment configuration. In other words, define the layout of your plate
# configure the experiment by parsing a configuration file
expt.set_config_from_file('configuration_file.txt')

# ...or configure it using set_config()
expt.set_config(['Group1', 'Group2'], ['Sample1', 'Sample2', 'Sample3'])

# Summarize the data and graph
expt.summarize('data_file.csv')
expt.graph('data.png')
```

### Documentation

[More in-depth documentation with an example experiment](https://github.com/cwrussell/bioscreen/edit/master/example/example.md) is found in the example folder. This includes an example of an [experiment configuration file](https://github.com/cwrussell/bioscreen/blob/master/example/data.config)

#### Further documentation is found in the module. Use bioscreen?, or Experiment.summarize?, for example.

