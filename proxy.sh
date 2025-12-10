sudo bash -c 'cat > /etc/profile.d/proxy.sh << "EOF"
#!/bin/bash
# V2RayN TUN 模式专用的最省流量代理设置（绕过大陆地址）
export http_proxy="http://192.168.0.8:10809"
export https_proxy="http://192.168.0.8:10809"
export ftp_proxy="http://192.168.0.8:10809"

# 大写版本（某些工具只认大写）
export HTTP_PROXY="http://192.168.0.8:10809"
export HTTPS_PROXY="http://192.168.0.8:10809"
export FTP_PROXY="http://192.168.0.8:10809"

# 关键！！！最省流量的 no_proxy 设置（V2RayN “绕过大陆地址”规则）
# 下面这些地址全部直连，完全不走代理流量
export no_proxy="localhost,127.0.0.1,::1,\
10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,\
.local,.cn,qq.com,taobao.com,360.cn,360.com,jd.com,alipay.com,\
xiaomi.net,mi.com,weibo.com,bilibili.com,youku.com,tudou.com,\
iqiyi.com,acfun.cn,baidu.com,tmall.com,alibaba.com,alicdn.com,\
pchome.net,github.com.cn,ctrip.com,163.com,126.com,sohu.com,\
sina.com.cn,zhihu.com,douyin.com,kuaishou.com"

export NO_PROXY="$no_proxy"

# 额外加两行，让 git、docker、apt 也完美识别（很多教程漏了这两行）
export ALL_PROXY="http://192.168.0.8:10809"
export all_proxy="http://192.168.0.8:10809"
EOF'

# 给执行权限并立即对当前终端生效
sudo chmod +x /etc/profile.d/proxy.sh
source /etc/profile.d/proxy.sh