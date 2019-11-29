from paddle_fl.core.trainer.fl_trainer import FLTrainerFactory
from paddle_fl.core.master.fl_job import FLRunTimeJob
import paddle_fl.dataset.femnist
import numpy
import sys
import paddle
import paddle.fluid as fluid
import logging
import math

logging.basicConfig(filename="test.log", filemode="w", format="%(asctime)s %(name)s:%(levelname)s:%(message)s", datefmt="%d-%M-%Y %H:%M:%S", level=logging.DEBUG)

trainer_id = int(sys.argv[1]) # trainer id for each guest
job_path = "fl_job_config"
job = FLRunTimeJob()
job.load_trainer_job(job_path, trainer_id)
job._scheduler_ep = "127.0.0.1:9091"
print(job._target_names)
trainer = FLTrainerFactory().create_fl_trainer(job)
trainer._current_ep = "127.0.0.1:{}".format(9000+trainer_id)
trainer.start()
print(trainer._step)
test_program = trainer._main_program.clone(for_test=True)

img = fluid.layers.data(name='img', shape=[1, 28, 28], dtype='float32')
label = fluid.layers.data(name='label', shape=[1], dtype='int64')
feeder = fluid.DataFeeder(feed_list=[img, label], place=fluid.CPUPlace())

def train_test(train_test_program, train_test_feed, train_test_reader):
        acc_set = []
        for test_data in train_test_reader():
            acc_np = trainer.exe.run(
                program=train_test_program,
                feed=train_test_feed.feed(test_data),
                fetch_list=["accuracy_0.tmp_0"])
            acc_set.append(float(acc_np[0]))
        acc_val_mean = numpy.array(acc_set).mean()
        return acc_val_mean

epoch_id = 0
step = 0
epoch = 3000
count_by_step = False
if count_by_step:
	output_folder = "model_node%d" % trainer_id
else: 
	output_folder = "model_node%d_epoch" % trainer_id
	

while not trainer.stop():
    count = 0
    epoch_id += 1
    if epoch_id > epoch:
        break
    print("epoch %d start train" % (epoch_id))
    #train_data,test_data= data_generater(trainer_id,inner_step=trainer._step,batch_size=64,count_by_step=count_by_step)
    train_reader = paddle.batch(
        paddle.reader.shuffle(paddle_fl.dataset.femnist.train(trainer_id,inner_step=trainer._step,batch_size=64,count_by_step=count_by_step), buf_size=500),
        batch_size=64)

    test_reader = paddle.batch(
        paddle_fl.dataset.femnist.test(trainer_id,inner_step=trainer._step,batch_size=64,count_by_step=count_by_step), batch_size=64) 
    
    
    if count_by_step:
    	for step_id, data in enumerate(train_reader()):
            acc = trainer.run(feeder.feed(data), fetch=["accuracy_0.tmp_0"])
            step += 1
            count += 1
	    print(count)
            if count % trainer._step == 0: 
                break
    # print("acc:%.3f" % (acc[0]))
    else:
        trainer.run_with_epoch(train_reader,feeder,fetch=["accuracy_0.tmp_0"],num_epoch=1) 
    

    acc_val = train_test(
        train_test_program=test_program,
        train_test_reader=test_reader,
        train_test_feed=feeder)

    print("Test with epoch %d, accuracy: %s" % (epoch_id, acc_val))
    if trainer_id == 0:  
    	save_dir = (output_folder + "/epoch_%d") % epoch_id
    	trainer.save_inference_program(output_folder)
