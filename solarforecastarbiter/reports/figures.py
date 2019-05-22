"""
Functions to make all of the figures for Solar Forecast Arbiter reports.
"""
import textwrap

from bokeh.models import ColumnDataSource
from bokeh.models.ranges import Range1d
from bokeh.models.widgets import DataTable, TableColumn, NumberFormatter
from bokeh.plotting import figure
from bokeh.transform import factor_cmap
from bokeh import palettes

import pandas as pd
import numpy as np


PALETTE = palettes.d3['Category10'][6]
_num_obs_colors = 3
OBS_PALETTE = palettes.grey(_num_obs_colors+1)[0:_num_obs_colors]  # drop white
OBS_PALETTE.reverse()
OBS_PALETTE_TD_RANGE = pd.timedelta_range(
    freq='10min', end='60min', periods=_num_obs_colors)

START_AT_ZER0 = ['mae', 'rmse']


def format_variable_name(variable, units):
    """Make a nice human readable name."""
    caps = ('ac_', 'dc_', 'poa_', 'ghi', 'dni', 'dhi')
    fname = variable
    for cap in caps:
        fname = fname.replace(cap, cap.upper())
    fname = fname.replace('_', ' ')
    return fname + f' ({units})'


def line_or_step(interval_label):
    if 'instant' in interval_label:
        plot_method = 'line'
        kwargs = dict()
    elif interval_label == 'beginning':
        plot_method = 'step'
        kwargs = dict(mode='before')
    elif interval_label == 'ending':
        plot_method = 'step'
        kwargs = dict(mode='after')
    return plot_method, kwargs


def construct_fx_obs_cds(fx_values, obs_values):
    """
    Construct a standardized Bokeh CDS for the plot functions.

    Parameters
    ----------
    fx_values : pandas.Series
    obs_values : pandas.Series

    Returns
    -------
    cds : bokeh.models.ColumnDataSource
        Keys are 'observation', 'forecast', and 'timestamp'.
    """
    data = pd.DataFrame({'observation': obs_values, 'forecast': fx_values})
    data = data.rename_axis('timestamp')
    cds = ColumnDataSource(data)
    return cds


def _obs_name(fx_obs):
    # TODO: add code to ensure obs names are unique
    name = fx_obs.observation.name
    if fx_obs.forecast.name == fx_obs.observation.name:
        name += ' Observation'
    return name


def _fx_name(fx_obs):
    # TODO: add code to ensure fx names are unique
    name = fx_obs.forecast.name
    if fx_obs.forecast.name == fx_obs.observation.name:
        name += ' Forecast'
    return name


def _obs_color(interval_length):
    idx = np.searchsorted(OBS_PALETTE_TD_RANGE, interval_length)
    obs_color = OBS_PALETTE[idx]
    return obs_color


def timeseries(fx_obs_cds, start, end):
    """
    Timeseries plot of one or more forecasts and observations.

    Parameters
    ----------
    obs_fx_cds : tuple of (ForecastObservation, cds) tuples
        ForecastObservation is a datamodel.ForecastObservation object.
        cds is a Bokeh ColumnDataSource with columns
        timestamp, observation, forecast.
    start : pandas.Timestamp
        Report start time
    end : pandas.Timestamp
        Report end time

    Returns
    -------
    fig : bokeh.plotting.figure
    """

    palette = iter(PALETTE)

    fig = figure(
        sizing_mode='scale_width', plot_width=900, plot_height=300,
        x_range=(start, end), x_axis_type='datetime',
        tools='pan,wheel_zoom,reset',
        name='timeseries')

    plotted_objects = []
    for fx_obs, cds in fx_obs_cds:
        if fx_obs.observation in plotted_objects:
            pass
        else:
            plotted_objects.append(fx_obs.observation)
            plot_method, kwargs = line_or_step(
                fx_obs.observation.interval_label)
            name = _obs_name(fx_obs)
            obs_color = _obs_color(fx_obs.observation.interval_length)
            getattr(fig, plot_method)(
                x='timestamp', y='observation', source=cds,
                color=obs_color, legend=name,  **kwargs)
        if fx_obs.forecast in plotted_objects:
            pass
        else:
            plotted_objects.append(fx_obs.forecast)
            plot_method, kwargs = line_or_step(
                fx_obs.forecast.interval_label)
            name = _fx_name(fx_obs)
            getattr(fig, plot_method)(
                x='timestamp', y='forecast', source=cds,
                color=next(palette), legend=name,  **kwargs)

    fig.legend.location = "top_left"
    fig.legend.click_policy = "hide"
    fig.xaxis.axis_label = 'Time (UTC)'
    fig.yaxis.axis_label = format_variable_name(fx_obs.forecast.variable,
                                                fx_obs.forecast.units)
    return fig


def _get_scatter_limits(fx_obs_cds):
    extremes = []
    for _, cds in fx_obs_cds:
        for kind in ('forecast', 'observation'):
            extremes.append(cds.data[kind].min())
            extremes.append(cds.data[kind].max())
    return min(extremes), max(extremes)


def scatter(fx_obs_cds):
    """
    Scatter plot of one or more forecasts and observations.

    Parameters
    ----------
    obs_fx_cds : tuple of (ForecastObservation, cds) tuples
        ForecastObservation is a datamodel.ForecastObservation object.
        cds is a Bokeh ColumnDataSource with columns
        timestamp, observation, forecast.

    Returns
    -------
    fig : bokeh.plotting.figure
    """
    xy_min, xy_max = _get_scatter_limits(fx_obs_cds)

    fig = figure(
        plot_width=450, plot_height=400, match_aspect=True,  # does not work?
        x_range=Range1d(xy_min, xy_max), y_range=Range1d(xy_min, xy_max),
        tools='pan,wheel_zoom,reset',
        name='scatter')

    kwargs = dict(size=6, line_color=None)

    palette = iter(PALETTE)

    for fx_obs, cds in fx_obs_cds:
        fig.scatter(
            x='observation', y='forecast', source=cds,
            fill_color=next(palette), legend=fx_obs.forecast.name, **kwargs)

    fig.legend.location = "top_left"
    fig.legend.click_policy = "hide"
    label = format_variable_name(fx_obs.forecast.variable,
                                 fx_obs.forecast.units)
    fig.xaxis.axis_label = 'Observed ' + label
    fig.yaxis.axis_label = 'Forecast ' + label
    return fig


def construct_metrics_cds(metrics, kind, index='metric'):
    """
    Possibly bad assumptions:
    * metrics contains keys: name, total, month, day, hour

    Parameters
    ----------
    metrics : list of metrics dicts
    kind : str
        One of total, month, day, hour
    index : str
        Determines if the index is the array of metrics ('metric') or
        forecast ('forecast') names

    Returns
    -------
    cds : bokeh.models.ColumnDataSource
    """
    if kind == 'total':
        df = pd.DataFrame({m['name']: m[kind] for m in metrics})
    df = df.rename_axis(index='metric', columns='forecast')
    if index == 'metric':
        pass
    elif index == 'forecast':
        df = df.T
    else:
        raise ValueError('index must be metric or forecast')
    cds = ColumnDataSource(df)
    return cds


def bar(cds, metric):
    """
    Create a table of metrics

    Parameters
    ----------
    cds : bokeh.models.ColumnDataSource
        Fields must be 'forecast' and the names of the metrics.

    Returns
    -------
    data_table : bokeh.widgets.DataTable
    """
    x_range = cds.data['forecast']
    # TODO: add units to title
    fig = figure(x_range=x_range, width=400, height=400, title=metric.upper())
    fig.vbar(x='forecast', top=metric, width=0.8, source=cds,
             line_color='white',
             fill_color=factor_cmap('forecast', PALETTE, factors=x_range))
    fig.xgrid.grid_line_color = None
    if metric in START_AT_ZER0:
        fig.y_range.start = 0
    else:
        # TODO: add heavy 0 line
        pass
    return fig


def nested_bar():
    raise NotImplementedError


def _table_title(name):
    # bokeh doesn't care :(
    title = '\n'.join(textwrap.wrap(name, width=15))
    return title


def metrics_table(cds):
    """
    Create an ugly, poorly formatted Bokeh table of metrics

    Parameters
    ----------
    cds : bokeh.models.ColumnDataSource
        Fields must be 'metric' and the names of the forecasts.

    Returns
    -------
    data_table : bokeh.widgets.DataTable
    """
    # construct list of columns. make sure that metric is first
    columns = [TableColumn(field='metric', title='Metric')]
    for field in filter(lambda x: x != 'metric', cds.data):
        title = _table_title(field)
        col = TableColumn(field=field, title=title)
        columns.append(col)
    data_table = DataTable(source=cds, columns=columns,
                           width=500, height=200, index_position=None)
    return data_table


def joint_distribution():
    raise NotImplementedError


def marginal_distribution():
    raise NotImplementedError


def taylor_diagram():
    raise NotImplementedError


def probabilistic_timeseries():
    raise NotImplementedError


def reliability_diagram():
    raise NotImplementedError


def rank_histogram():
    raise NotImplementedError
