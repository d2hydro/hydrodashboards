# %%

"""
Analyze logs from IIS.
Filter unique IPs to get indication of traffic on egv dashboard
"""

import datetime
from pathlib import Path

import numpy as np
import pandas as pd

LOG_DIR = Path(r"..\..\logs\iis_logging")

ips = []
dates = []
unique_ip_cumsum = {}
for log in LOG_DIR.glob("*.log"):
    a = log.read_text()
    b = a.split(
        "#Fields: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) cs(Referer) sc-status sc-substatus sc-win32-status time-taken X-Forwarded-For"
    )[1:]

    for c in b:
        d = c.split("\n")
        for row in d:
            if len(row) > 100:
                ip = row[-20:].split(",+")[-1].split(" ")[-1]
                if len(ip) > 5:
                    ip = ip.split(":")[0]
                    dates.append(row[:10])
                    ips.append(ip)
                    # print(len(row))

    date_obj = datetime.datetime.strptime(log.stem[4:-2], "%y%m%d").strftime("%Y-%m-%d")
    unique_ip_cumsum[date_obj] = len(set(ips)) - 1

df = pd.DataFrame([dates, ips]).T
df = df.rename(columns={0: "date", 1: "unique_ip"})

df_agg = df.groupby("date").agg(lambda x: len(np.unique(x)))
df_agg["unique_ip"] -= 1  # Remove load balancer, assume 1 unique ip per day

# Users come back after a day, we dont count those here
unique_ip_cumsum_df = pd.DataFrame(list(unique_ip_cumsum.items()), columns=["date", "lifetime_unique_ip"])

# Merge DataFrames
df_agg = df_agg.merge(unique_ip_cumsum_df, on="date", how="left")

display(df_agg)

print(f"Sum unique_ip per day: {df_agg['unique_ip'].sum()}")

# Display log messages per ip
df["cnt"] = 1
a = (
    df.groupby("unique_ip")
    .agg(
        {"cnt": "sum", "date": lambda x: len(np.unique(x))},
    )
    .sort_values("cnt", ascending=False)
).rename(columns={"date": "unique_dates"})
a[a["unique_dates"] != len(unique_ip_cumsum)].head()  # filter load balancer, sees board every day.

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# Create DataFrame
df_plot = df_agg.copy()
df_plot.reset_index(inplace=True)
df_plot["date"] = pd.to_datetime(df_plot["date"])

# Plotting
fig, ax1 = plt.subplots()

# Bar graph for unique_ip
xcolor = "orange"
ax1.bar(df_plot["date"], df_plot["unique_ip"], color=xcolor, label="Unique IP")
# ax1.set_xlabel("Date")
ax1.set_ylabel("Unique IP", color=xcolor)
ax1.tick_params(axis="y", labelcolor=xcolor)

# Rotate the ticks and display data every week
# ax1.xaxis.set_major_locator(plt.MultipleLocator(7))  # Display every week
ax1.xaxis.set_major_locator(mdates.MonthLocator())  # Display every month
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
plt.xticks(rotation=45)

# Line graph for lifetime_unique_ip
x2color = "black"
ax2 = ax1.twinx()
ax2.plot(df_plot["date"], df_plot["lifetime_unique_ip"], color=x2color, label="Lifetime Unique IP")
ax2.set_ylabel("Lifetime Unique IP", color=x2color)
ax2.tick_params(axis="y", labelcolor=x2color)

# Title and legend
plt.title("Gebruik EGV dashboard")
fig.tight_layout()
plt.show()

fig.savefig(LOG_DIR / f"gebruik_egv_{datetime.datetime.now().strftime('%Y%m%d')}.png")
