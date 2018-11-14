# Documentation (With an Example Experiment)

## The Experiment

An experiment was run in the Bioscreen C where 6 bacterial strains were grown in 3 different media 
for 24 h with readings taken every 20 minutes. Some wells were included as "blanks", meaning that they
contained only media, no bacteria. These wells serve as background readings that can be subtracted
from the other wells that contain the same medium.

In the documentation, each media condition will be called a "group", and each strain a "sample". 
The blank is also considered a "sample".

The data was exported as .csv file as "data.csv"


## Defining the Configuration of the Experiment

To analyze and graph the data, you first need to define the groups and samples of the experiment.
This can be done three different ways:
(1) Experiment.set_config_from_file(), which requires creating a configuration file
(2) Experiment.set_config(), which allows you to simply list the groups and samples
(3) manually setting Experiment.configuration, which is probably most helpful for small experiments (see below)

In this example, we will create a configuration file. The file must be tab-delimited with one row
for each set of wells. The fields are (1) Group (i.e. condition), (2) Sample, (3) Wells. See [data.config](https://github.com/cwrussell/bioscreen/edit/master/example/data.config)
for the full file, but here are the first few lines:

```
LB      blank   1-4
LB      Strain1 5-8 
LB      Strain2 9-12
```

"blank" is a keyword that indicates that the readings from these wells should be subtracted from all
of the other wells in the group. Blank readings are not required for this module to work.

Well numbers can be given in the format of start-stop (e.g. 1-4), or as comma-separated values (e.g. 1,2,3,4)

The configuration file is loaded with Experiment.set_config_from_file('data.config')

This configuration could have also been done with the following commands:

```
import bioscreen
expt = bioscreen.Experiment()
expt.set_config(['LB', 'M9-glucose', 'M9-rhamnose'], ['blank', 'Strain1', 'Strain2', 'Strain3', 'Strain4', 'Strain5', 'Strain6')
```

In this case, using set_config() would be quicker. However, for experiments that are not as rigidly structured,
a configuration file would be easiest. Use set_config? for more information.


## Summarizing the Data

The data are summarized by averaging the readings for each set of wells at each time point. The blank
readings (if available) are then subtracted from readings in the same group at the same time point.

```
# first, import the module and initialize a new Experiment
import bioscreen
expt = bioscreen.Experiment()

# second, load the configuration file
expt.set_config_from_file('data.config')

# summarize the data and write the summary file
expt.summarize('data.csv')
expt.write_summary('data.summary.csv')
```

The resulting summary file will have a Time column, and then a column for each set of wells that are
labeled as Group__Sample.


## Graphing the Data

The data from the above example can now be graphed:

```
expt.graph('data.png')
```

You can also create separate graphs for each group:

```
expt.graph_groups('data')
```

Use Experiment.graph? to see the many graphing options that are available.


## Loading a Previously-Made Summary File

It is possible to skip the configuration step and create graphs from a summary file previously made
from Experiment.write_summary()

```
expt.load_summary('data.summary.csv')
```

## Setting Timepoints

The default unit for timepoints is hours, but minutes and days could also be used. This is set
in Experiment.summarize()

```
expt.summarize('data.csv', timepoints='minutes')
```

The default label for the X axis when graphing is "Time (h)". This can also be changed:

```
expt.graph('data.png', xlabel='Time (min)')
```

The timepoints in the original Bioscreen C file can be replaced with custom timepoints by passing a
list to timepoints in summarize().


## Manually Setting Experiment.configuration

For a small or oddly-designed experiment, setting the configuration manually might be easiest.
self.configuration is a list of dictionaries with keys=samples, and values=wells. Each dictionary
has an additional 'group' key that is set to the group name.

For example, if two samples plus a blank were run in duplicate wells in two different conditions,
the configuration could be set like this:

```
expt.configuration = [ {'group': 'condition1', 'blank': [1,2], 'sample1': [3,4], 'sample2': [5,6]}, {'group': 'condition2', 'blank': [7,8], 'sample1': [9,10], 'sample2': [11,12]} ]
```

## The w() Function

w(x, y) creates a list from x to y. This function can be a helpful shorthand when setting the configuration manually.

```
w(1,6)
print(w)
# [1, 2, 3, 4, 5, 6]
```
