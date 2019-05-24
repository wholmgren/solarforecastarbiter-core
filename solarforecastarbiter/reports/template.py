"""
Inserts metadata and figures into the report template.
"""
import subprocess

from bokeh.embed import components
from bokeh.layouts import column

from jinja2 import (Environment, DebugUndefined, PackageLoader,
                    select_autoescape, Template, Markup)

from solarforecastarbiter.reports import figures


def prereport(report, metadata, metrics):
    """
    Render the markdown prereport. Figures are left untemplated.

    Parameters
    ----------
    report : solarforecastarbiter.datamodel.Report
        Metadata describing report
    metadata : str, dict
        Describes the pre-report
    metrics : tuple of dict

    Returns
    -------
    prereport : markdown
    """
    # By default, jinja removes undefined variables from the rendered string.
    # DebugUndefined leaves undefined variables in the string so that they
    # can be used in the full report template process.
    env = Environment(
        loader=PackageLoader('solarforecastarbiter.reports', 'templates'),
        autoescape=select_autoescape(['html', 'xml']),
        undefined=DebugUndefined)

    template = env.get_template('template.md')

    fx_obs = [[fx_obs.observation.name,
               getattr(fx_obs.observation, 'uuid', ''),
               fx_obs.forecast.name,
               getattr(fx_obs.forecast, 'uuid', '')]
              for fx_obs in report.forecast_observations]

    cds = figures.construct_metrics_cds(metrics, 'total', index='forecast')
    data_table = figures.metrics_table(cds)

    figures_bar = []
    for num, metric in enumerate(report.metrics):
        fig = figures.bar(cds, metric)
        figures_bar.append(fig)

    script, (data_table_div, *figures_bar_divs) = components((data_table,
                                                              *figures_bar))

    figures_bar_month = []
    # series with MultiIndex of metric, forecast, month
    metrics_series = figures.construct_metrics_series(metrics, 'month')
    for num, metric in enumerate(report.metrics):
        cds = figures.construct_metrics_cds2(metrics_series, metric)
        figs = figures.bar_subdivisions(cds, 'month', metric)
        figures_bar_month.append(column(figs))

    script_month, figures_bar_month_divs = components(figures_bar_month)

    figures_bar_day = []
    # series with MultiIndex of metric, forecast, day
    metrics_series = figures.construct_metrics_series(metrics, 'day')
    for num, metric in enumerate(report.metrics):
        cds = figures.construct_metrics_cds2(metrics_series, metric)
        figs = figures.bar_subdivisions(cds, 'day', metric)
        figures_bar_day.append(column(figs))

    script_day, figures_bar_day_divs = components(figures_bar_day)

    figures_bar_hour = []
    # series with MultiIndex of metric, forecast, hour
    metrics_series = figures.construct_metrics_series(metrics, 'hour')
    for num, metric in enumerate(report.metrics):
        cds = figures.construct_metrics_cds2(metrics_series, metric)
        figs = figures.bar_subdivisions(cds, 'hour', metric)
        figures_bar_hour.append(column(figs))

    script_hour, figures_bar_hour_divs = components(figures_bar_hour)

    script_metrics = script + script_month + script_day + script_hour

    strftime = '%Y-%m-%d %H:%M:%S'

    rendered = template.render(
        name=metadata['name'],
        start=metadata['start'].strftime(strftime),
        end=metadata['end'].strftime(strftime),
        now=metadata['now'].strftime(strftime),
        fx_obs=fx_obs,
        validation_issues=metadata['validation_issues'],
        versions=metadata['versions'],
        script_metrics=script_metrics,
        tables=data_table_div,
        figures_bar=figures_bar_divs,
        figures_bar_month=figures_bar_month_divs,
        figures_bar_day=figures_bar_day_divs,
        figures_bar_hour=figures_bar_hour_divs)
    return rendered


def _loop_over_metrics():
    pass


# not all args currently used, but expect they will eventually be used
def add_figures_to_prereport(fx_obs_cds, report, metadata, prereport,
                             html=True):
    """
    Add figures to the prereport, convert to html

    Parameters
    ----------
    fx_obs_cds : list
        List of (forecast, observation, ColumnDataSource) tuples to
        pass to bokeh plotting objects.
    report : solarforecastarbiter.datamodel.Report
        Metadata describing report
    metadata : str, dict
        Describes the pre-report
    prereport : str, markdown or html
        The templated pre-report.
    html : bool
        Indicates if the template will be rendered into html or pdf.

    Returns
    -------
    body : str, markdown or html
        The body of the full report in the same format
        (markdown or html) as the prereport.
    """
    body_template = Template(prereport)

    ts_fig = figures.timeseries(fx_obs_cds, report.start, report.end)
    scat_fig = figures.scatter(fx_obs_cds)

    script, divs = components(
        {'figures_timeseries': ts_fig, 'figures_scatter': scat_fig})

    body = body_template.render(
        script_data=script,
        html=html,
        **divs)
    return body


def prereport_to_html(prereport):
    """
    Render markdown into simple html using pandoc.

    Parameters
    ----------
    prereport : str, markdown

    Returns
    -------
    prereport : str, html
    """
    try:
        out = subprocess.run(args=['pandoc', '--from', 'markdown+pipe_tables'],
                             input=prereport.encode(), capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise OSError('Error converting prereport to html using pandoc') from e
    return out.stdout.decode()


def full_html(body):
    """Create full html file.

    The Solar Forecast Arbiter dashboard will likely use its own
    templates for rendering the full html.

    Parameters
    ----------
    body : html

    Returns
    -------
        head : str, html
        Header for the full report.
    """
    env = Environment(
        loader=PackageLoader('solarforecastarbiter.reports', 'templates'),
        autoescape=select_autoescape(['html', 'xml']))
    base_template = env.get_template('base.html')

    base = base_template.render(body=body)

    return base
