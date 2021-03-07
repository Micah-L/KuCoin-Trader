# Copyright 2021 Micah Loverro
# Loverro Software Consulting
# Permission is hereby granted, to any person obtaining a copy of this software and associated documentation files (the "Software"),
# to use or copy this software. Permission is not granted to publish, distribute, sublicense, and/or sell copies of the Software.
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDER BE LIABLE 
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. THE AUTHOR OR COPYRIGHT HOLDERS SHALL NOT BE RESPONSIBLE FOR ANY LOSS 
# OF PROPERTY OR ASSETS FROM USING THIS SOFTWARE.

This software requires python 3 (recommended: 3.9.1)

Installation:
1. Install python,
2. Open up a terminal and run 
pip install kucoin
or
python -m pip install kucoin-python
3. Log in to KuCoin, and generate your API key. Then open the file 'config.py' and fill in the lines:
    API_PASSPHRASE = "your-passphrase-here"
    API_KEY = "your-api-key-here"
    API_SECRET = "your-api-secret-here"
with your actual API key, secret, and passphrase. Be sure to include the quotation marks around these credentials.

Running:
1. Open up a terminal in the location that these files are in.
If on windows, you can do this opening file explorer at the location the files are in, and typing cmd in the address bar, and hitting enter. Otherwise, open up a terminal and type cd /path/to/these/files
2. Run the program by with the command
python kutrader.py
3. To stop the program, hit ctrl+c, or type quit into the terminal and hit enter. 