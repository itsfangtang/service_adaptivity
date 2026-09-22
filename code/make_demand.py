import numpy as np, csv
r=list(csv.reader(open('demo_sensor_demand_30x24.csv')))
np.save('demand.npy',np.array([[float(v) for v in row[1:]] for row in r[1:]]))
