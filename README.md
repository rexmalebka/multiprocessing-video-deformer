# multiprocessing-video-deformer
 video deformer created using python as a multiprocessing demostration for myself


## requirements
- opencv
- python 3
- numpy


## how to use

- Run the server:
> python server.py

- run a client elsewhere 
> python -i client.py

- load a video and send the load command
> s0.load('videos/video.mp4').send()



## commands and variables

There are two variables string available `frame` and `buffer[::]`, you can use them to specify the current played frame or a buffer of saved frames (buffer is a list)

### s0.do

you need to add sequencial actions in order to modify the frame, pass the parameters as the normal function would do, for example:
> s0.do(cv2.erode, 'frame', np.ones((10,1), np.uint8)).send()

would be the equivalent of this:

`frame = cv2.erode(frame,np.ones((10,1), np.uint8))`

### s0.send()

as all the actions are saved sequencially in `s0.actions` you need to send them in order to start modifying the frames

### s0.clear()

this clears the actions list

### s0.resolution( width, height )

you can change the video resolution 

### with s0 as s:

you can use this in order to make  multiple  actions over the same frame

```python
with s0 as s:
    for k in range(0,10):
        s.do(cv2.addWeighted, 'buffer[-2]', 2,f'fbuffer[{k}]', -1, 0)
s0.send()
```

guess that's all 




