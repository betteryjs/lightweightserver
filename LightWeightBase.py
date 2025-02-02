import json
import time
from threading import Thread, Event
from croniter import croniter
from datetime import datetime

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkswas_open.request.v20200601.StartInstanceRequest import StartInstanceRequest
from aliyunsdkswas_open.request.v20200601.StopInstanceRequest import StopInstanceRequest
from aliyunsdkswas_open.request.v20200601.RebootInstanceRequest import RebootInstanceRequest

from aliyunsdkswas_open.request.v20200601.ListDisksRequest import ListDisksRequest
from aliyunsdkswas_open.request.v20200601.CreateSnapshotRequest import CreateSnapshotRequest
from aliyunsdkswas_open.request.v20200601.ListSnapshotsRequest import ListSnapshotsRequest
from aliyunsdkswas_open.request.v20200601.DeleteSnapshotRequest import DeleteSnapshotRequest
from aliyunsdkswas_open.request.v20200601.ListInstancesTrafficPackagesRequest import ListInstancesTrafficPackagesRequest
from aliyunsdkswas_open.request.v20200601.ListInstancesRequest import ListInstancesRequest
from aliyunsdkswas_open.request.v20200601.ResetSystemRequest import ResetSystemRequest
from aliyunsdkswas_open.request.v20200601.UpdateInstanceAttributeRequest import UpdateInstanceAttributeRequest
from aliyunsdkswas_open.request.v20200601.LoginInstanceRequest import LoginInstanceRequest
from aliyunsdkswas_open.request.v20200601.DescribeInstanceVncUrlRequest import DescribeInstanceVncUrlRequest
from aliyunsdkswas_open.request.v20200601.CreateFirewallTemplateRequest import CreateFirewallTemplateRequest
from aliyunsdkswas_open.request.v20200601.DescribeFirewallTemplatesRequest import DescribeFirewallTemplatesRequest
from aliyunsdkswas_open.request.v20200601.ApplyFirewallTemplateRequest import ApplyFirewallTemplateRequest
from aliyunsdkswas_open.request.v20200601.CreateFirewallTemplateRulesRequest import CreateFirewallTemplateRulesRequest
from aliyunsdkswas_open.request.v20200601.DeleteFirewallTemplateRulesRequest import DeleteFirewallTemplateRulesRequest
from aliyunsdkswas_open.request.v20200601.ListFirewallRulesRequest import ListFirewallRulesRequest
from aliyunsdkswas_open.request.v20200601.DeleteFirewallRuleRequest import DeleteFirewallRuleRequest
from aliyunsdkswas_open.request.v20200601.DeleteFirewallTemplatesRequest import DeleteFirewallTemplatesRequest
from aliyunsdkswas_open.request.v20200601.ResetDiskRequest import ResetDiskRequest

from loguru import logger


class Light:
    def __init__(self, LightConfig):
        self.AccessKeyId = LightConfig["AccessKeyId"]
        self.AccessKeySecret = LightConfig["AccessKeySecret"]
        self.region_id = LightConfig["region_id"]
        self.InstanceId = LightConfig["InstanceId"]
        self.password = LightConfig["DefaultPassword"]
        self.endpoint = f"swas.{self.region_id}.aliyuncs.com"
        self.SnapshotCrons = LightConfig["SnapshotCrons"]

        self.credentials = AccessKeyCredential(self.AccessKeyId, self.AccessKeySecret)
        self.client = AcsClient(region_id=self.region_id, credential=self.credentials)

        self.autoSnapshotId = ""

        self.DiskId = ""
        self.GetDiskId()
        self.FirewallTemplateId = ""
        if self.FindAutoFirewallTemplate() is False:
            self.CreateAutoFirewallTemplate()
        self.ApplyFirewallTemplate()

        # timmer
        # 定时器存储
        self.timers = {}

        # 初始化定时器，但不启动
        self.initialize_timer('AutoSnapshot', self.SnapshotCrons, self.CreateAutoSnapshot)

        self.SnapshotName_SnapshotId = {}
        self.ShowSnapshots()

    def schedule_cron(self, cron_expression, stop_event, job):
        base_time = datetime.now()
        cron = croniter(cron_expression, base_time)

        while not stop_event.is_set():
            next_run = cron.get_next(datetime)
            sleep_duration = (next_run - datetime.now()).total_seconds()

            if sleep_duration > 0:
                stop_event.wait(sleep_duration)
                if not stop_event.is_set():
                    job()

    def initialize_timer(self, timer_id, cron_expression, job):
        stop_event = Event()
        self.timers[timer_id] = {
            'cron_expression': cron_expression,
            'job': job,
            'stop_event': stop_event,
            'thread': None
        }

    def start_timer(self, timer_id):
        if timer_id in self.timers and self.timers[timer_id]['thread'] is None:
            cron_expression = self.timers[timer_id]['cron_expression']
            job = self.timers[timer_id]['job']
            stop_event = self.timers[timer_id]['stop_event']
            t = Thread(target=self.schedule_cron, args=(cron_expression, stop_event, job))
            self.timers[timer_id]['thread'] = t
            t.start()

    def stop_timer(self, timer_id):
        if timer_id in self.timers and self.timers[timer_id]['thread'] is not None:
            self.timers[timer_id]['stop_event'].set()
            self.timers[timer_id]['thread'].join()
            self.timers[timer_id]['thread'] = None

    def is_timer_running(self, timer_id):
        return timer_id in self.timers and self.timers[timer_id]['thread'] is not None

    def StartInstance(self):
        request = StartInstanceRequest()
        request.set_accept_format('json')

        request.set_InstanceId(self.InstanceId)
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        msg = f"Start instance {self.InstanceId} successfully"
        logger.success(msg)
        return msg

    def StopInstance(self):
        request = StopInstanceRequest()
        request.set_accept_format('json')

        request.set_InstanceId(self.InstanceId)
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        msg = f"Stop instance {self.InstanceId} successfully"
        logger.success(msg)
        return msg

    def RebootInstance(self):
        request = RebootInstanceRequest()
        request.set_accept_format('json')

        request.set_InstanceId(self.InstanceId)
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        msg = f"Reboot instance {self.InstanceId} successfully"
        logger.success(msg)
        return msg

    def IsStoppedInstance(self):
        request = ListInstancesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceIds(str([self.InstanceId]))

        response = json.loads(self.client.do_action_with_exception(request).decode())
        for Instance in response['Instances']:
            if Instance["InstanceId"] == self.InstanceId:
                logger.info(f"Instance Status is {Instance['Status']}")
                if Instance['Status'] == "Stopped":
                    return True
                else:
                    return False

                # Pending：准备中。
                # Starting：启动中。
                # Running：运行中。
                # Stopping：停止中。
                # Stopped：停止。
                # Resetting：重置中。
                # Upgrading：升级中。
                # Disabled：不可用。

    def GetDiskId(self):
        request = ListDisksRequest()
        request.set_accept_format('json')
        request.set_InstanceId(self.InstanceId)
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        self.DiskId = response["Disks"][0]["DiskId"]
        logger.info(f"get DiskId success and DiskId is {self.DiskId}")

    def CreateAutoSnapshot(self):
        if self.SnapshotIsExists("AutoSnapshot"):
            self.DeleteAutoSnapshot()
        time.sleep(5)
        self.CreateSnapshot("AutoSnapshot")

    def CreateSnapshot(self, name):

        # if not exists to do create
        request = CreateSnapshotRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_DiskId(self.DiskId)
        request.set_SnapshotName(f"{name}")

        response = json.loads(self.client.do_action_with_exception(request).decode())
        self.SnapshotName_SnapshotId[name] = response['SnapshotId']
        msg = f"create {name} Snapshot success! and SnapshotId  is {response['SnapshotId']}"
        logger.success(msg)
        return msg

    def ListSnapshots(self):

        request = ListSnapshotsRequest()
        request.set_accept_format('json')

        request.set_InstanceId(self.InstanceId)
        request.set_DiskId(self.DiskId)
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        return response['Snapshots']

    def ShowSnapshots(self):

        request = ListSnapshotsRequest()
        request.set_accept_format('json')

        request.set_InstanceId(self.InstanceId)
        request.set_DiskId(self.DiskId)
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())

        for Snapshot in response['Snapshots']:
            self.SnapshotName_SnapshotId[Snapshot["SnapshotName"]] = Snapshot["SnapshotId"]
        return self.SnapshotName_SnapshotId

    def AutoSnapshotIsExists(self):
        return self.SnapshotIsExists("AutoSnapshot")

    def SnapshotIsExists(self, name):
        Snapshots = self.ListSnapshots()
        for Snapshot in Snapshots:
            if Snapshot["SnapshotName"] == name:
                logger.info(f"find {name} Snapshot success and SnapshotId is {Snapshot['SnapshotId']}")
                return True
        logger.info(f"{name} Snapshot not exists!")
        return False

    def SnapshotIsExistsByID(self, ID):
        Snapshots = self.ListSnapshots()
        for Snapshot in Snapshots:
            if Snapshot["SnapshotId"] == ID:
                logger.info(
                    f"find {Snapshot['SnapshotName']} Snapshot success and SnapshotId is {Snapshot['SnapshotId']}")
                return True
        logger.info(f"{ID} Snapshot not exists!")
        return False

    def DeleteAutoSnapshot(self):
        self.DeleteSnapshot("AutoSnapshot")

    def DeleteSnapshot(self, name):
        if self.SnapshotIsExists(name):
            request = DeleteSnapshotRequest()
            request.set_accept_format('json')
            request.set_endpoint(self.endpoint)

            request.set_SnapshotId(self.SnapshotName_SnapshotId[name])

            response = self.client.do_action_with_exception(request).decode('utf-8')
            logger.success(f"delete {name} Snapshot success!")
            logger.success(response)
            self.SnapshotName_SnapshotId.pop(name)
        else:
            logger.error(f"{name} Snapshot not exists!")

    def DeleteSnapshotByID(self, ID):
        if self.SnapshotIsExistsByID(ID):
            request = DeleteSnapshotRequest()
            request.set_accept_format('json')
            request.set_endpoint(self.endpoint)

            request.set_SnapshotId(ID)

            response = self.client.do_action_with_exception(request).decode('utf-8')
            msg = f"delete {ID} Snapshot success!"
            logger.success(msg)
            return msg

        else:
            msg = f"{ID} Snapshot not exists!"
            logger.error(msg)
            return msg

    def ResetDiskByID(self, ID):
        if not self.IsStoppedInstance():
            self.StopInstance()
            time.sleep(15)
        request = ResetDiskRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_DiskId(self.DiskId)
        request.set_SnapshotId(ID)

        response = self.client.do_action_with_exception(request).decode('utf-8')
        logger.info(response)
        time.sleep(15)
        self.StartInstance()

    def ResetDisk(self, name):

        if not self.IsStoppedInstance():
            self.StopInstance()
            time.sleep(15)
        request = ResetDiskRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_DiskId(self.DiskId)
        request.set_SnapshotId(self.SnapshotName_SnapshotId[name])

        response = self.client.do_action_with_exception(request).decode('utf-8')
        logger.info(response)
        time.sleep(15)
        self.StartInstance()

    def ListInstancesTrafficPackages(self):
        request = ListInstancesTrafficPackagesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceIds(str([self.InstanceId]))

        response = json.loads(self.client.do_action_with_exception(request).decode())
        if not response["InstanceTrafficPackageUsages"]:
            # 200M
            return "200M包带宽"
        else:

            TrafficUsed = response["InstanceTrafficPackageUsages"][0]["TrafficUsed"] / (1024 ** 3)
            TrafficPackageTotal = response["InstanceTrafficPackageUsages"][0]["TrafficPackageTotal"] / (1024 ** 3)

            return str(TrafficUsed) + "GB / " + str(TrafficPackageTotal) + "GB"

    def ResetSystem(self):
        request = ResetSystemRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)
        request.set_ImageId("8b798eb927684a08b26bb95da94f5812")
        request.set_InstanceId(self.InstanceId)
        response = json.loads(self.client.do_action_with_exception(request).decode())
        msg = "Reset System to Debian 11 !"
        logger.success(msg)
        return msg

    def UpdateInstancePassward(self):
        request = UpdateInstanceAttributeRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceId(self.InstanceId)
        request.set_Password(self.password)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        msg = f"change password success! and password is {self.password}"
        logger.success(msg)
        return msg

    def LoginInstanceSshUrl(self):
        request = LoginInstanceRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceId(self.InstanceId)
        request.set_Port(22)

        response = json.loads(self.client.do_action_with_exception(request).decode())

        logger.success(f"get Ssh Url Success! and url is {response['RedirectUrl']}")
        return response['RedirectUrl']

    def LoginInstanceVncUrl(self):
        request = DescribeInstanceVncUrlRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceId(self.InstanceId)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        logger.success(f"get VNC Url Success! and url is {response['VncUrl']}")
        return response["VncUrl"]

    def CreateAutoFirewallTemplate(self):
        request = CreateFirewallTemplateRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        # query_param = {
        #     'RegionId': "cn-hongkong",
        #     'Name': "AutoFirewall",
        #     'FirewallRule.1.RuleProtocol': "TCP+UDP",
        #     'FirewallRule.1.SourceCidrIp': "0.0.0.0/0",
        #     'FirewallRule.1.Port': "1/65535",
        #     'FirewallRule.2.RuleProtocol': "ICMP",
        #     'FirewallRule.2.Port': "-1",
        #     'FirewallRule.2.SourceCidrIp': "0.0.0.0/0",
        # }
        # for k, v in query_param.items():
        #     request.add_query_param(k, v)

        # query_param = {
        #     'RegionId': "cn-hongkong",
        #     'Name': "AutoFirewall"
        # }
        request.set_Name("AutoFirewall")
        # for k, v in query_param.items():
        #     request.add_query_param(k, v)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        self.FirewallTemplateId = response['FirewallTemplateId']
        logger.success(f"CreateAutoFirewallTemplate success! and FirewallTemplateId is {self.FirewallTemplateId} ")
        return self.FirewallTemplateId

    def FindAutoFirewallTemplate(self):
        request = DescribeFirewallTemplatesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        for FirewallTemplate in response["FirewallTemplates"]:
            if FirewallTemplate["Name"] == "AutoFirewall":
                self.FirewallTemplateId = FirewallTemplate['FirewallTemplateId']
                logger.success(f"find AutoFirewallTemplate success! FirewallTemplateId is {self.FirewallTemplateId}")
                return True
        logger.info("AutoFirewallTemplate not find !")
        return False

    def ApplyFirewallTemplate(self):
        request = ApplyFirewallTemplateRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceIdss([self.InstanceId])
        request.set_FirewallTemplateId(self.FirewallTemplateId)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        logger.success(f"FirewallTemplate {self.FirewallTemplateId} Apply to Instance {self.InstanceId}!")

    def CreateFirewallTemplateRules(self):

        request = CreateFirewallTemplateRulesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_FirewallTemplateId(self.FirewallTemplateId)

        query_param = {
            'RegionId': "cn-hongkong",
            'Name': "AutoFirewall",
            'FirewallRule.1.RuleProtocol': "TCP+UDP",
            'FirewallRule.1.SourceCidrIp': "0.0.0.0/0",
            'FirewallRule.1.Port': "1/65535",
            'FirewallRule.1.Remark': "AutoFirewallRules",
            'FirewallRule.2.RuleProtocol': "ICMP",
            'FirewallRule.2.Port': "-1",
            'FirewallRule.2.SourceCidrIp': "0.0.0.0/0",
            'FirewallRule.2.Remark': "AutoFirewallRules",

        }
        for k, v in query_param.items():
            request.add_query_param(k, v)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        logger.success("CreateFirewallTemplateRules success!")
        self.ApplyFirewallTemplate()

    def FirewallTemplateRuleId(self):
        request = DescribeFirewallTemplatesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        for FirewallTemplate in response["FirewallTemplates"]:
            if FirewallTemplate["Name"] == "AutoFirewall":
                FirewallTemplateRules = FirewallTemplate["FirewallTemplateRules"]
                return [FirewallTemplateRule['FirewallTemplateRuleId'] for FirewallTemplateRule in
                        FirewallTemplateRules]

    def FirewallRuleId(self):
        request = ListFirewallRulesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_InstanceId(self.InstanceId)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        AutoFirewallRulesId = []

        for FirewallRule in response["FirewallRules"]:
            if FirewallRule["Remark"] == "AutoFirewallRules":
                AutoFirewallRulesId.append(FirewallRule["RuleId"])
        logger.info(AutoFirewallRulesId)
        return AutoFirewallRulesId

    def DeleteFirewallTemplateRules(self):
        request = DeleteFirewallTemplateRulesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_FirewallTemplateId(self.FirewallTemplateId)

        request.set_FirewallTemplateRuleIds(self.FirewallTemplateRuleId())

        response = json.loads(self.client.do_action_with_exception(request).decode())
        logger.success("DeleteFirewallTemplateRules success!")
        # self.ApplyFirewallTemplate()

    def DeleteFirewallRules(self):

        for FirewallRule in self.FirewallRuleId():
            request = DeleteFirewallRuleRequest()
            request.set_accept_format('json')
            request.set_endpoint(self.endpoint)

            request.set_InstanceId(self.InstanceId)

            request.set_RuleId(FirewallRule)
            response = json.loads(self.client.do_action_with_exception(request).decode())
            logger.success(f"DeleteFirewallRules success! and FirewallRuleID is {FirewallRule}")

    def DeleteFirewallTemplates(self):
        request = DeleteFirewallTemplatesRequest()
        request.set_accept_format('json')
        request.set_endpoint(self.endpoint)

        request.set_FirewallTemplateIds([self.FirewallTemplateId])

        response = json.loads(self.client.do_action_with_exception(request).decode())
        logger.success("DeleteFirewallTemplates success!")


# if __name__ == '__main__':
#     with open("config.json", 'r') as file:
#         configJson = json.loads(file.read())
#     for LightConfig in configJson['LightConfig']:
#         print(LightConfig)
#         light = Light(LightConfig)
#         # print(light.GetBandwidth())
#         # light.CreateFirewallTemplateRules()
#         # light.DeleteFirewallTemplateRules()
#         # light.FirewallRuleId()
#         # print(light.FirewallRuleId())
#         #
#         # light.DeleteFirewallRules()
#         # light.DeleteFirewallTemplates()
