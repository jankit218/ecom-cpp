echo "all services are validated"

echo "removing the code-agent"
sudo dpkg --purge codedeploy-agent

echo "deleting the codeagent dir"
sudo rm -rf /opt/codedeploy-agent/

echo "killing the codeagent processes"

#sudo ps -fu root | grep codedeploy | awk -F" " '{print $2}'  > /dev/null 2>&1 &


if sudo ps -fu 'root' | grep codedeploy
then
PID=`sudo ps -fu root | grep codedeploy | awk -F" " '{print $2}' | head -1`; 
sudo kill -9 $PID; 
while [ -e /proc/$PID ]; 
do echo "Process: $PID is still running" > /home/ubuntu/pid.log;
sleep .6; 
done; 
echo "Process $PID has finished" >> /home/ubuntu/pid.log; 
else
echo "no process running as codeagent"
fi

echo "installing the codeagent"
cd /home/ubuntu/
sudo ./install auto > /dev/null 2>&1 &