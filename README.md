# Tora Backend

This repository contains the code for the Tora Electric Bus simulator backend. Below are steps to properly configure the project and run it locally.

## Steps

### Prerequisites

Ensure that you have the following installed
- git
- python (3.9)

Dependencies in this project specifically depend on python 3.9. Using a later version could result in parts of the application failing, so installing v3.9 is highly recommended for this project.

### 1. Clone the Repository

Open a terminal or shell and navigate to a location of your choosing. Then run the following command:

```
git clone https://github.com/khatmpeers/tora-backend.git
cd tora-backend
```

### 2. Create a Virtual Environment

MacOS
```
python3.9 -m venv venv // use direct install
// or
(pyenv install 3.9) // use pyenv
pyenv local 3.9
python -m venv venv
```

Windows
```
(py install 3.9) //assuming the latest python version manager
py -3.9 -m venv venv
```

### 3. Install Dependencies

```
pip install -r backend/requirements.txt
```

### 4. Start Backend

```
fastapi dev backend/app/main.py
```

### 5. Verify Backend Status

Confirm that the corresponding [backend](https://github.com/khatmpeers/tora-frontend) is installed and running on the same device.
