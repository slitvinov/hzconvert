import pandas, sys
df = pandas.read_csv(sys.argv[1])
num = df.select_dtypes("number")
summary = pandas.DataFrame({
    "min":    num.min(),
    "max":    num.max(),
    "nan":    num.isna().sum(),
    "n":      num.count(),
    "unique": num.nunique(),
})
print(summary.to_string(float_format="{:.2f}".format))
