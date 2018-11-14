#!/usr/bin/env python3

"""
The bioscreen module analyzes and graphs growth curves from Bioscreen C data

See example folder on GitHub for a step-by-step example and more in-depth documentation.

## Basic example
# create new Experiment object
import bioscreen
expt = bioscreen.Experiment()

# configure the Experiment, i.e. define what each well is.
# there are 3 options. See documentation for each for more information
expt.set_config_from_file(config_file_path)
expt.set_config([groups], [samples])
expt.configuration = [{'group': 'group1', 'blank': [1,2,3,4], 'sample1': [5,6,7,8]}, {'group': 'group2', ...}, ...]

# summarize/analyze the experiment
# in this step, the readings for each set of wells is averaged at each time point
# the blank well readings, if available, are subtracted from the sample readings
expt.summarize()

# output the summary data if desired
expt.write_summary(summary_file)

# graph the data
expt.graph(figure_file)


## It is also possible to create graphs from previously-made summary files
expt = bioscreen.Experiment()
expt.load_summary(summary_file)
expt.graph(figure_file)


## Instead of graphing everything at once, selected data can be graphed
# graphing data just for "group1" and "group2"
expt.graph(figure_file, groups_to_graph=['group1', 'group1'])

# graphing just "sample1" in "group1"
expt.graph(figure_file, samples_go_graph=['group1__sample1'])

# or creating a graph for each group
expt.graph_groups('figure_base_name')
"""


import re

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class Experiment:

  def __init__(self):
    """
    Experiment objects are used to analyze and graph bioscreen data.
    The basic workflow is:
    (1) use Experiment.set_config() or .set_config_from_file() to define the experiment configuration 
    (2) summarize data with Experiment.summarize()
    (3) graph data with Experiment.graph()

    See documentation for the bioscreen module and for each method for more information
    """
    self.configuration = None
    self.summary_data = None
    self.data_path = None
    self.summary_path = None


  def status(self):
    report = 'An Experiment object in the bioscreen module\n'
    if self.configuration is not None:
      report = report + '\nExperimental configuration: ' + str(self.configuration) + '\n'
    else:
      report = report + '\nExperimental configuration is not set.\n'
    if self.summary_data is not None:
      report = report + '\nData has been summarized.\n\tData File: {}\n\tSummary File: {}'.format(self.data_path, self.summary_path)
    else:
      report = report + '\nData has not been summarized yet.'
    return report


  def __str__(self):
    return self.status()

  def __repr__(self): 
    return self.status()


  def load_summary(self, summary_path):
    """
    Load summary data that was previously created by Experiment.write_summary()

    Arguments:
    (1) path to summary file.
    """
    self.summary_data = pd.read_table(summary_path)
    self.summary_path = summary_path
    summary_columns = [x for x in self.summary_data.columns if x != 'Time']
    self.groups = []
    for column in summary_columns:
      curr_group = column.split('__')[0]
      if curr_group not in self.groups: self.groups.append(curr_group)
    self.timepoints = list(self.summary_data.Time)


  def summarize(self, data_path, timepoints='hours', input_encoding='utf_16_le', rows_to_skip=2, sep=','):
    """
    Load raw bioscreen data, average across wells for each sample, subtract out blank values

    Arguments:
    (1) path to data file

    - timepoints='hours'
        Units to use for the timepoints. Accepted values are 'minutes', 'hours',
        'days', or a list of the timepoints

    - input_encoding='utf_16_le'

    - rows_to_skip=2
        Number of rows that are skipped when reading in the file.
        .csv and .txt files from the bioscreen have 2 lines before the row containing column
        headers.

    - sep=','
        The separator/delimiter used in the file
        Default is ',' for .csv files
        Set to '\s+' for .txt files
    """
    # make sure data configuration has already occurred
    if self.configuration is None:
      raise RuntimeError('Experiment must be configured prior to summarizing the data')

    # load data
    self.data_path = data_path
    self.loaded_data = pd.read_csv(self.data_path, encoding=input_encoding, skiprows=rows_to_skip, sep=sep)

    ## Deal with the time points
    # if a list was given, make sure it is of the right length
    if isinstance(timepoints, np.ndarray):
      timepoints = list(timepoints)

    if isinstance(timepoints, list):
      if len(timepoints) != self.loaded_data.shape[0]:
        raise RuntimeError('List given in timepoints argument is not of correct length. Data has length of %s, while time is of length %s'
          % (self.loaded_data.shape[0], len(timepoints)))
      else: self.timepoints = timepoints

    # otherwise, convert the timepoints to the desired unit
    elif isinstance(timepoints, str):

      # make sure the timepoints argument can be understood
      timepoints_possible = ['days', 'hours', 'minutes', 'd', 'h', 'm', 'min', 'mins', 'day', 'hour']
      timepoints = timepoints.lower()
      if timepoints not in timepoints_possible:
        raise RuntimeError('Timepoints argument not a valid value: days, hours, or minutes')

      time_column = self.loaded_data.Time

      # make sure in format HH:MM:SS
      time_format_error = 'Time values not in expected format, which is HH:MM:SS'
      test_time = time_column[0].split(':')
      if len(test_time) != 3: raise RuntimeError(time_format_error)
      for tt in test_time:
        if len(tt) != 2: raise RuntimeError(time_format_error)

      # convert the time appropriately
      new_time_column = []
      for tm in time_column:
        tm_spl = [int(x) for x in tm.split(':')]
        tm_mins = tm_spl[1] + (tm_spl[2] / 60)
        tm_hours = tm_spl[0] + (tm_mins / 60)
        if (timepoints in ('minutes', 'min', 'mins', 'm')):
          new_time = tm_mins + (tm_spl[0] * 60)
        elif (timepoints in ('hours', 'hour', 'h')):
          new_time = tm_hours
        elif (timepoints in ('days', 'day', 'd')):
          new_time = tm_hours / 24
        else:
          raise RuntimeError('Timepoints argument not a valid value: days, hours, or minutes')
        new_time_column.append(new_time)

      self.timepoints = new_time_column

    # was given something weird in the timepoints argument
    else: raise RuntimeError('The timepoints argument must be either a list or a string')


    ## build a data frame in which the data have been blanked and averaged
    self.summary_data = pd.DataFrame({'Time': self.timepoints})

    # iterate over the groups in the experiment
    for group in self.configuration:

      # (1a) Get the mean blank reading at each time point
      if ('blank' in group):
        blank_columns = [str(x) for x in group['blank']]
        blank_df = self.loaded_data.filter(blank_columns, axis=1)
        blank_mean = blank_df.mean(axis=1)

      # (1b) If no blank in the group, set up all blank readings as 0
      else:
        blank_mean = pd.Series([0] * self.loaded_data.shape[0])

      # (2) Get the mean value for each sample in the group, subtract the blank mean value
      group_df = pd.DataFrame()
      for sample, columns in list(group.items()):
        if (sample == 'group') or (sample == 'blank'): continue
        columns = [str(x) for x in columns]
        sample_df = self.loaded_data.filter(columns, axis=1)
        sample_mean = sample_df.mean(axis=1)
        sample_blanked = sample_mean - blank_mean
        #sample_column = pd.Series([group['group']]).append(sample_blanked)
        column_name = '%s__%s' % (group['group'], sample)
        group_df[column_name] = sample_blanked

      # (3) Add to summary_data
      self.summary_data = pd.concat([self.summary_data, group_df], axis=1)


  def write_summary(self, output_file):
    """
    Output summary data to tab-delimited file.
    Summary data is averaged, blanked and has group and sample descriptions

    Positional Arguments:
    (1) output file path
    """
    self.summary_data.to_csv(output_file, sep='\t', index=False)
    self.summary_path = output_file


  def graph_groups(self, output_file_base, **kwargs):
    """
    Create a separate graph for each group.

    Positional Arguments:
    (1) base name for output files
      '.groupname.png' will be added to the base name

    See bioscreen.graph for key word arguments
    """
    if self.summary_data is None:
      raise RuntimeError('Data must be summarized prior to graphing')

    for group in self.groups:
      file_name = output_file_base + '.' + group + '.png'
      self.graph(file_name, groups_to_graph=[group], **kwargs)


  def graph(self, output_file, size_inches=(8, 8), title=False, xlabel='Time (h)',
    ylabel='OD600', line_colors='rainbow', legend=True, marker='o',
    linestyle='-', markersize=3, addlabels=False, groups_to_graph=False,
    samples_to_graph=False, **kwargs):
    """
    Graph the data

    Positional Arguments:
    (1) output file name (.png)

    Key Word Arguments:
    - size_inches=(8, 8)
        width and height of figure in inches

    - title=False
        Title for the figure

    - xlabel='Time (h)'
         Label for the x axis

    - ylabel='OD600'
         Label for the y axis

    - line_colors='rainbow'
        Can be a string, with either a matplotlib colormap (see https://matplotlib.org/users/colormaps.html)
        or a single color (e.g. 'blue') that will be used for all lines.
        Can also be a list of colors that is equal in length to the number of samples graphed.

    - legend=True
        Add a legend to the figure.

    - marker='o'
        Marker to use for each data point. See https://matplotlib.org/api/markers_api.html

    - linestyle='-'
        Type of line to use. Use '--' for dashed line.

    - markersize=3
        Size of marker

    - addlabels=False
        If True, the sample names will be added at the end of the curves.

    - groups_to_graph=False
        To graph specific groups instead of all of the data, set to a list of the groups
        e.g. ['LB', 'M9']

    - samples_to_graph=False
        To graph specific samples instead of all of the data, set to a list of the samples
        e.g. ['LB__WT', 'M9-glu__WT', 'M9-rha__WT']

    Other key word arguments that are recognized by matplotlib.pyplot.plot may be used.
    """
    if self.summary_data is None:
      raise RuntimeError('Data must be summarized prior to graphing')

    fig = plt.figure(figsize=size_inches)

    # get data and labels into lists
    y_data = [ list(self.summary_data[x]) for x in self.summary_data.columns if x != 'Time' ]
    y_labels = [ x for x in self.summary_data.columns if x != 'Time' ]
    x_time = list(self.summary_data['Time'])

    ## prune the data and labels lists if only specific groups were asked for
    if (groups_to_graph is not False) and (samples_to_graph is not False):
      print('Warning. Both groups_to_graph and samples_to_graph were defined. Using samples_to_graph')

    # if specific samples to graph
    if (samples_to_graph is not False):
      new_y_data = []
      new_y_labels = []
      for i in range(len(y_data)):
        if y_labels[i] in samples_to_graph:
          new_y_data.append(y_data[i])
          new_y_labels.append(y_labels[i])
      y_data = new_y_data
      y_labels = new_y_labels

      # see if all samples found
      for sample in samples_to_graph:
        if sample not in y_labels: print('Warning. Sample %s not found' % sample)

    # if wanting to graph specific groups
    if (groups_to_graph is not False) and (samples_to_graph is False):
      found_groups = []
      new_y_data = []
      new_y_labels = []
      for i in range(len(y_data)):
        curr_group = y_labels[i].split('__')[0]
        if (curr_group in groups_to_graph):
          new_y_data.append(y_data[i])
          new_y_labels.append(y_labels[i])
          if curr_group not in found_groups: found_groups.append(curr_group)
      y_data = new_y_data
      y_labels = new_y_labels

      # see if all groups found
      for group in groups_to_graph:
        if group not in found_groups: print('Warning. Group %s not found' % group)

    # set up the colors
    if isinstance(line_colors, str):
      try:
        color_map = plt.get_cmap(line_colors)
        line_colors = color_map(np.linspace(0, 1, len(y_data)))
      except:
        line_colors = [ line_colors ] * len(y_data)

    # graph lines
    for i in np.arange(len(y_data)):
      plt.plot(x_time, y_data[i], marker=marker, linestyle=linestyle, markersize=markersize,
               color=line_colors[i], label=y_labels[i], **kwargs)

    # title and axis labels
    if title is not False: plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    # add labels to lines
    if addlabels is True:
      for i in np.arange(len(y_data)):
        plt.text(x_time[-1], y_data[i][-1], y_labels[i], color=line_colors[i], ha='center')

    # adding a legend and saving
    if legend is True:
      lgd = plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
      plt.savefig(output_file, bbox_extra_artists=(lgd,), bbox_inches='tight')
    else:
      plt.savefig(output_file, bbox_inches='tight')

    plt.cla()
    plt.clf()
    plt.close()


  def set_config(self, groups, samples, replicates=4, wells=False):
    """
    Experiment.set_config() allows you to set the configuration by providing a list of the
    experimental groups and a list of samples. Configuration can also be set from a file,
    see set_config_from_file(). In either case, the end result is that self.config is set
    to a list where each element is a dictionary representing a group/condition with keys
    being the sample name (or "blank") and the values being a list of wells. self.config
    can also be set directly
  
    Positional Arguments:
    (1) a list of group names, e.g. ['LB', 'M9', ...]
    (2) a list of samples
        If of a single depth (a simple list), e.g. ['blank', 'WT', 'mutant', ...]
        the list will be repeated for each group.
  
        If a list of lists, each item in the list is a group, e.g.
        [ ['group1_blank', 'group1_WT', 'group1_mutant'], ['group2_blank', ...] ]
  
        *** Note that 'blank' is a keyword. If included in the list of samples, all other
            samples in that group will be normalized to the blank samples, meaning that
            the average blank reading at each time point is subtracted from the sample
            readings.
  
    Key Word Arguments:
    - replicates=4
        The number of wells per sample.
  
    - wells=False
        If False, the wells that correspond to each sample are figured out from
        the list of groups, samples, and the number of replicates.
        To give the lists explicitly, set wells to a list of well groups, e.g.
        [ [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12] ]
  
    Examples:
    (1) Simplest scenario with two strains grown in two growth conditions in quadruplicate
    config(['LB', 'M9'], ['blank', 'WT', 'KO'])
     [ {'KO': [9, 10, 11, 12],
        'WT': [5, 6, 7, 8],
        'blank': [1, 2, 3, 4],
        'group': 'LB'},
       {'KO': [21, 22, 23, 24],
        'WT': [17, 18, 19, 20],
        'blank': [13, 14, 15, 16],
        'group': 'M9'} ]
  
    (2) Experiment where the strains grown in the different conditions are not the same
    config(['LB', 'M9'], [ ['blank', 'WT', 'KO'], ['blank', 'KO1', 'KO2', 'KO3'] ])
     [ {'KO': [9, 10, 11, 12],
        'WT': [5, 6, 7, 8],
        'blank': [1, 2, 3, 4],
        'group': 'LB'},
       {'KO1': [17, 18, 19, 20],
        'KO2': [21, 22, 23, 24],
        'KO3': [25, 26, 27, 28],
        'blank': [13, 14, 15, 16],
        'group': 'M9'} ]
  
    (3) Experiment done in triplicate where a well needs to be excluded due to pipetting error
    config(['LB', 'M9'], ['blank', 'WT', 'KO'], wells=[ [1,2,3], [4,5,6], [7,9], [10,11,12], [13,14,15], [16,17,18] ])
      [ {'KO': [7, 9], 'WT': [4, 5, 6], 'blank': [1, 2, 3], 'group': 'LB'},
        {'KO': [16, 17, 18], 'WT': [13, 14, 15], 'blank': [10, 11, 12], 'group': 'M9'} ]
  
    """
  
    # turn samples list into a list of lists if repeat_samples is True
    if isinstance(samples[0], str):
      samples_list = [samples] * len(groups)
    elif isinstance(samples[0], list):
      samples_list = samples
    else:
      raise RuntimeError('Unable to understand the samples list.')
  
    # the groups list length and the samples_list length should be equal at this point
    if (len(groups) != len(samples_list)):
      raise RuntimeError('Groups and Samples lists should be equal in length.\nGroups: %s\nSamples: %s' % (groups, samples_list))
  
    # figure out how many sets of well numbers are needed
    num_well_groups = 0
    for sample_list in samples_list:
      for sample in sample_list: num_well_groups += 1
  
  
    # create a list of lists for the well numbers as explained in the documentation
    if wells is False:
  
      # create start and stop well numbers to be used to make wells list
      replicates = int(replicates)
      starts_max_range = (num_well_groups * replicates) + 1
      starts = np.arange(1, starts_max_range, replicates)
      stops_max_range = starts_max_range + replicates
      stops = np.arange(1 + replicates, stops_max_range, replicates)
  
      # now populate the wells list
      wells = []
      for i in range(num_well_groups):
        wells.append(list(np.arange(starts[i], stops[i])))
  
    # if wells list is provided, it should be length of the number of well groups
    else:
      if (len(wells) != num_well_groups):
        raise RuntimeError('The length of the provided list of wells does not match the number of needed well groups.\nlen(wells): %s\nshould be %s' % (len(wells), num_well_groups))
  
    # now create the configuration list
    config_list = []
    g = 0    # keeps track of the group that we're on
    w = 0    # keeps track of the well list that we're on
    for group in samples_list:
      group_dict = {'group': groups[g]}
      for sample in group:
        group_dict[sample] = wells[w]
        w += 1
      g += 1
      config_list.append(group_dict)
  
    self.configuration = config_list
    self.groups = groups
  

  def set_config_from_file(self, config_path):
    """
    set_config_from_file() will configure an Experiment by parsing a configuration file

    The file should be tab-delimited with one row for each set of data to be graphed. For example,
    if I grew WT or mutant cells in LB and M9 media, one set of data would be WT cells grown in LB media.
 
    Columns in the file are:
    (1) Group/condition
    (2) Sample name or "blank"
    (3) Wells (e.g. 1-4 or 1,2,3,4)
    """
    groups = []
    group_config = {} # keys = group name, values are dictionary with keys=sample, values=[wells]
    self.config_path = config_path

    # parse file, populate groups and group_config
    with open(self.config_path, 'r') as config_file:
      for line in config_file:
        if line.startswith('#'): continue
        ls = line.rstrip().split('\t')
        if len(ls) != 3: print('Error in configuration file format on line: {}'.format(line))
        group = rename_strict(ls[0])
        if group.lower() == 'blank': group = 'blank'
        sample = rename_strict(ls[1])
        wells_notation = ls[2]
        if '-' in wells_notation:
          wells_spl = wells_notation.split('-')
          wells = w(int(wells_spl[0]), int(wells_spl[1]))
        if ',' in wells_notation:
          wells_spl = wells_notation.split(',')
          wells = [int(x) for x in wells_spl]
        if group not in groups: groups.append(group)
        if group not in group_config: group_config[group] = {sample: wells}
        else: group_config[group][sample] = wells

    # use group_config dictionary to make self.configuration dictionary
    self.groups = groups
    self.configuration = []
    for group in self.groups:
      new_group = {'group': group}
      for sample in group_config[group]:
        new_group[sample] = group_config[group][sample]
      self.configuration.append(new_group)


def w(a, b):
  """
  w() will return a list of consecutive integers from a to b
  it is equivalent to list(range(a,b+1,1))
  """
  return list(range(a, b+1))


def rename_strict(file_name):
  """ 
  rename_strict takes a file name (or just a string) and replaces all unwanted characters with
  an underscore, then shortens the name so that there aren't two or more underscores
  in a row

  Allowed characters = A-Z, a-z, 0-9, _, -, ., /
  """
  scrubbed_name = re.sub('[^A-Za-z0-9_\-./]', '_', file_name.strip())
  rm_underscores = scrubbed_name.strip('_')
  while '__' in rm_underscores: rm_underscores = re.sub('__', '_', rm_underscores)
  return rm_underscores

