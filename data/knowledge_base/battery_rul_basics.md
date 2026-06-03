# Battery RUL Monitoring Notes

## RUL and SoH

Remaining Useful Life (RUL) is an estimate of the remaining operating cycles before a battery reaches a defined end-of-life threshold. State of Health (SoH) is commonly expressed as a capacity ratio relative to the initial capacity. A monitoring dashboard should clearly state the selected threshold and should not treat a predicted value as a guaranteed lifetime.

## Early-cycle prediction

In an operational setting, the complete lifetime trajectory of a newly monitored battery is unavailable. Early-cycle prediction therefore uses an initial observation window to estimate a longer degradation trajectory. The observation ratio, battery-level validation split, and possible data leakage must be recorded when reporting model performance.

## Data quality checks

Before modeling, cycle order, missing values, duplicate records, abnormal capacity changes, and differences in experimental conditions should be reviewed. Voltage, current, temperature, capacity, and impedance-related features may require separate checks because their availability and meaning can differ across datasets.

## Interpreting uncertainty

A point estimate alone can hide prediction risk. A dashboard can display an uncertainty band together with the estimated RUL, SoH, and degradation trend. The uncertainty band should be described as a model estimate rather than a certified safety boundary.

