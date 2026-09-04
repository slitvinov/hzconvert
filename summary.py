import pandas, sys
try:
    df = pandas.read_csv(sys.argv[1])
except IndexError:
    sys.stderr.write("summary.py: error: needs an argument\n")
    exit(1)
except FileNotFoundError as e:
    sys.stderr.write("summary.py: error: fail to read '%s'\n" % e.filename)
    exit(1)
num = df.select_dtypes("number")
summary = pandas.DataFrame({
    "obs": num.count(),
    "mean": num.mean(),
    "std": num.std(),
    "min": num.min(),
    "max": num.max(),
    "nan": num.isna().sum(),
    "unique": num.nunique(),
})
print(summary.to_string(float_format="{:.1f}".format))

