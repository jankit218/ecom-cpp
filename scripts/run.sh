
#Run the application

sudo chmod -R 775 /home/ubuntu/cpp/myproj

cd /home/ubuntu/cpp
python3 -m venv venv
source /home/ubuntu/cpp/venv/bin/activate

cd /home/ubuntu/cpp/myproj
pip install -r requirements.txt

sudo chown ubuntu:ubuntu *

echo "Running the application"
cd /home/ubuntu/cpp/myproj
python3 manage.py runserver 0.0.0.0:8000 >> /dev/null 2>&1 &

