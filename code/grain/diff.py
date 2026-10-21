import sys
a=open(sys.argv[1],'rb').read()
b=open(sys.argv[2],'rb').read()
assert len(a)==len(b), (len(a),len(b))
# group contiguous runs of differing bytes
runs=[]
i=0
n=len(a)
while i<n:
    if a[i]!=b[i]:
        j=i
        while j<n and a[j]!=b[j]:
            j+=1
        runs.append((i,j))
        i=j
    else:
        i+=1
print(f"total differing bytes: {sum(j-i for i,j in runs)}")
print(f"number of runs: {len(runs)}")
for (i,j) in runs:
    print(f"\n[{i:#08x} .. {j:#08x})  len={j-i}")
    print("  old:", a[i:j].hex())
    print("  new:", b[i:j].hex())
