import configparser
import logging
import re
import time
import traceback
from pprint import pprint

import cv2
from airtest.core.android.adb import ADB
from airtest.core.android.android import Android
from airtest.core.android.constant import CAP_METHOD, ORI_METHOD, TOUCH_METHOD

logging.getLogger('airtest').setLevel(logging.WARNING)

android=None

def lerp(a,b,m,n):
    return (b-a)*m//n+a

class Base():
    def __init__(self,size):
        assert size in [3,4,5]
        self.size=size
        config=configparser.ConfigParser()
        config.read('config.ini')
        self.coord=eval(config[str(size)]['coord'])
        self.cancel=eval(config['DEFAULT']['cancel'])
        self.key={
            (i,j):(
                lerp(self.coord[0][0],self.coord[1][0],j,self.size-1),
                lerp(self.coord[0][1],self.coord[1][1],i,self.size-1),
            )
            for i in range(size)
            for j in range(size)
        }
        self.edgeCache={
            ((i,j),(i,j)):False
            for i in range(size)
            for j in range(size)
        }
        img=android.snapshot()[:,:,1]
        for i in range(size):
            for j in range(size):
                p=self.key[(i,j)]
                for m in range(-20,20):
                    for n in range(-20,20):
                        img[p[1]+n,p[0]+m]=0
        for i in range(size):
            for j in range(size):
                for m in range(size):
                    for n in range(size):
                        if ((i,j),(m,n))in self.edgeCache:
                            continue
                        p1=self.key[(i,j)]
                        p2=self.key[(m,n)]
                        for k in range(1,29):
                            if img[lerp(p1[1],p2[1],k,29)][lerp(p1[0],p2[0],k,29)]>240:
                                self.edgeCache[((i,j),(m,n))]=False
                                self.edgeCache[((m,n),(i,j))]=False
                                break
    def tap(self,p):
        android.touch(self.key[p])
    def undo(self):
        android.touch(self.cancel)
    def connect(self,p1,p2):
        def send(method,pos):
            android.touch_proxy.handle(' '.join((method,'0',*[str(i)for i in android.touch_proxy.transform_xy(*pos)],'50\nc\n')))
        p1=android._touch_point_by_orientation(self.key[p1])
        p2=android._touch_point_by_orientation(self.key[p2])
        time.sleep(.01)
        send('d',p1)
        # time.sleep(.01)
        # send('m',(p1[0],p1[1]-2))
        # time.sleep(.01)
        # send('m',(p1[0]+2,p1[1]))
        # time.sleep(.01)
        # send('m',(p2[0]-2,p2[1]))
        # time.sleep(.01)
        # send('m',(p2[0],p2[1]+2))
        time.sleep(.1)
        send('m',p2)
        time.sleep(.1)
        android.touch_proxy.handle('u 0\nc\n')
        time.sleep(.05)
    def isThereAnEdge(self,p1,p2):
        if (p1,p2)in self.edgeCache:
            return self.edgeCache[p1,p2]
        self.connect(p2,p1)
        ans=android.snapshot()[(self.key[p1][1]+self.key[p2][1])//2,(self.key[p1][0]+self.key[p2][0])//2][1]<150
        self.undo()
        self.undo()
        # if not ans:
        #     self.connect(p2,p1)
        #     ans=android.snapshot()[(self.key[p1][1]+self.key[p2][1])//2,(self.key[p1][0]+self.key[p2][0])//2][1]<150
        #     self.undo()
        #     self.undo()
        self.edgeCache[(p1,p2)]=ans
        self.edgeCache[(p2,p1)]=ans
        return ans

class Main:
    def __init__(self,size):
        self.base=Base(size)
        self.adjacent={
            i:j
            for i,j in{
                (i,j):{
                    (m,n)
                    for m in range(self.base.size)
                    for n in range(self.base.size)
                    if self.base.isThereAnEdge((i,j),(m,n))
                }
                for i in range(self.base.size)
                for j in range(self.base.size)
            }.items()
            if j
        }
        for i,j in self.adjacent.items():
            print(i,j,sep=':')
    def solve(self):
        go=[i for i,j in self.adjacent.items()if len(j)&1]
        assert len(go)in[0,2]
        dim=sum(len(i)for i in self.adjacent.values())//2
        way=[]
        flag=False
        def dfs(p):
            if len(way)==dim:
                nonlocal flag
                flag=True
                return
            for i in self.adjacent[p]:
                if (i,p)in way or(p,i) in way:
                    continue
                way.append((p,i))
                dfs(i)
                if flag:
                    return
                way.pop()
        dfs(go[0]if len(go)else list(self.adjacent)[0])
        print(way)
        self.way=way
        self.apply()
    def apply(self):
        self.base.connect(*self.way[0])
        for i in self.way[1:]:
            time.sleep(.02)
            self.base.tap(i[1])

if __name__=='__main__':
    devices=[i[0]for i in ADB().devices()if i[1]=='device']
    serial=devices[0]
    if len(devices)>1:
        print('\n'.join('\t'.join(str(j)for j in i)for i in enumerate(devices)))
        serial=devices[int(input())]
    android=Android(serial,ori_method=ORI_METHOD.ADB,touch_method=TOUCH_METHOD.MAXTOUCH)
    while True:
        try:
            print('size:',end='')
            Main(int(input())).solve()
        except:
            traceback.print_exc()
            continue
            