## v0.66.0
- feat: Added backtest queueing to dashboard
- fix: persist symbol presets across dashboard restarts
- fix: make parallel backtests thread-safe

## v0.65.1
- fix: restore progress bar on tab switch by querying running jobs on page load

## v0.65.0
- feat: add dashed plot styles and improve mkdocs readability
- feat: track indicator subpackages and fix gitignore scope
- feat: add user-configurable plot_color to indicators
- feat: changed charting

## v0.64.0
- feat: changed dashboard UI

## v0.63.0
- feat: added bollinger package, closes #16

## v0.62.0
- feat: fixed external strategy discovery

## v0.61.0
- feat: made indicators defineable externally

## v0.60.0
- feat: made strategies definable package externally
- docs: added tutorial for running dashboard locally

## v0.59.0
- feat: minimal version of dashboard completed

## v0.58.0
- feat: added performance tab to dashboard

## v0.57.0
- feat: added dashboard package

## v0.56.0
- feat: added orchestrator

## v0.55.0
- feat: added strategies package

## v0.54.0
- feat: added simulated datafeed

## v0.53.0
- feat: completed secmaster package

## v0.52.0
- feat: added secmaster package

## v0.51.0
- feat: added broker base and simulated broker

## v0.50.0
- feat: added messaging package

## v0.49.0
- feat: added indicators

## v0.48.0
- feat: added indicator base class

## v0.47.0
- feat: completed events package

## v0.46.0
- feat: added broker request events

## v0.45.0
- feat: added events package with EventBase class

## v0.44.0
- feat: complete rework, integrated models package

## v0.43.0
- feat: added signal validation to dashboard

## v0.42.0
- feat: added charting to dashboard

## v0.41.0
- feat: Added dashboard

## v0.40.0
- feat: added connectors simulated and IB

## v0.39.0
- feat: secmaster complete

## v0.38.0
- feat: fixed documentation

## v0.37.0
- feat: fixed imports
- feat: fixed module structure

## v0.36.0
- feat: update
- chore(ci): release 0.35.0
- feat: restructure

## v0.35.0
- feat: restructure

## v0.34.0
- feat: added datafeed base and simulated

## v0.33.0
- feat: updated indicators and strategies

## v0.32.0
- feat: added strategy base class

## v0.31.0
- feat: added sma to averages

## v0.30.0
- feat: added bar indicators

## v0.29.0
- feat: added indicator base

## v0.28.0
- feat: added simulated broker

## v0.27.0
- feat: added broker base class

## v0.26.0
- feat: added subscriber base class

## v0.25.0
- feat: restructured package

## v0.24.0
- feat: updated core

## v0.23.0
- feat: reworked core

## v0.22.0
- feat: added event syncinc for backtesting

## v0.21.0
- feat: consolidated rejection reason model

## v0.20.0
- feat: added datafeeds module

## v0.19.0
- feat: implemented order lifecycle events

## v0.18.0
- feat: added fill event message

## v0.17.0
- feat: Added core module

## v0.16.0
- feat: Reworked entire project

## v0.15.0
- feat: added minimal working portfolio class

## v0.14.2
- fix: updated portfolio class, added strategy event

## v0.14.1
- fix: Fixed mypy error in CI
- fix: Added incomplete packages for mypy CI check
- fix: Added StopStrategy event

## v0.14.0
- feat: added portfolio namespace to events

## v0.13.1
- fix: fixed docstring in sma class

## v0.13.0
- feat: added simple moving average implementation

## v0.12.1
- fix: documentation fixes in base indicator class

## v0.12.0
- feat: added indicator base class

## v0.11.0
- feat: added csv datafeed

## v0.10.1
- fix: removed bar preloading method from datafeeds

## v0.10.0
- feat: implemented datafeeds base class

## v0.9.0
- feat: implemented event bus

## v0.8.0
- feat: Added event message dataclasses
- docs: justified text via extra css
- docs: fixed script to generate api docs

## v0.7.0
- feat: restructured monitoring package
- docs: removed placeholders in docs website
- docs: added CI/CD pipeline to README.md
- docs: fixed source display in no content modules

## v0.6.0
- feat: removed complexity to rework
- docs: fixed link in api reference overview
- chore: removed coverage testing

## v0.5.3
- fix: removed event class from domain.models module
- docs: fixed links in documentation overview
- docs: fixed api-reference generation script

## v0.5.2
- fix: changed name from log_config to monitoring

## v0.5.1
- fix: restructured domain_models into domain module

## v0.5.0
- feat: re-added domain models module

## v0.4.0
- feat: general cleanup and updated documentation
- docs: fix docs website deploy issue

## v0.3.0
- feat: added domain_models module
- chore: fixed version bump to not patch by default

## v0.2.1
- docs: updated cicd pipeline documentation

## v0.2.0
- feat: added log_config and test_log_config
- docs: added documentation for cicd pipeline
