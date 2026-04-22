import deepgram

print("Available in deepgram module:")
for item in dir(deepgram):
    if not item.startswith('_'):
        print(f"  {item}")

print("\nAvailable in deepgram.listen:")
from deepgram import listen
for item in dir(listen):
    if not item.startswith('_'):
        print(f"  {item}")
