# including the latest numpy seems to be problematic in the snap
# for armhf. To avoid this if the snap contains a system numpy
# that is >= 1.26.4, the version in core24 then we will
# only use the system numpy provided by the OS

minversion = "1.26.4"
import os
from packaging.version import Version

def main():
    version = False
    try:
        import numpy
        version = numpy.__version__
        print(f"System numpy version: {version}")
    except:
        print("No system numpy found, skipping constraints.")

    output = ""
    if version is not False and Version(version) >= Version(minversion):
        print(f"Constraint added for numpy version: {version}")
        output = f"numpy=={version}\n"
    else:
        print(f"No constraint added for numpy version: {version}")
    with open(os.path.join(os.getcwd(),"constraints.txt"), "w") as f:
        f.write(output)

if __name__ == "__main__":
    main()


