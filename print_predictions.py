import sys
import os
from os import path
import numpy as np
import tensorflow as tf
from tensorflow.contrib import slim
from nets import inception
from preprocessing import inception_preprocessing

model_path = sys.argv[1]
image_dir = sys.argv[2]
gpu_memory_fraction = float(sys.argv[3])

if tf.gfile.IsDirectory(model_path):
    model_path = tf.train.latest_checkpoint(model_path)

image_names = sorted(os.listdir(image_dir))
image_paths = [path.join(image_dir, image_name) for image_name in image_names]

image_size = inception.inception_resnet_v2.default_image_size

with tf.Graph().as_default():
    # Inject placeholder into the graph
    input_image_t = tf.placeholder(tf.string, name='input_image')
    image = tf.image.decode_jpeg(input_image_t, channels=3)

    # Resize the input image, preserving the aspect ratio
    # and make a central crop of the resulted image.
    # The crop will be of the size of the default image size of
    # the network.
    # I use the "preprocess_for_eval()" method instead of "inception_preprocessing()"
    # because the latter crops all images to the center by 85% at
    # prediction time (training=False).
    processed_image = inception_preprocessing.preprocess_for_eval(image,
                                                                  image_size,
                                                                  image_size, central_fraction=None)

    # Networks accept images in batches.
    # The first dimension usually represents the batch size.
    # In our case the batch size is one.
    processed_images = tf.expand_dims(processed_image, 0)

    # Load the inception network structure
    with slim.arg_scope(inception.inception_resnet_v2_arg_scope()):
        logits, _ = inception.inception_resnet_v2(processed_images,
                                                  num_classes=2,
                                                  is_training=False)
    # Apply softmax function to the logits (output of the last layer of the network)
    probabilities = tf.nn.softmax(logits)

    # Get the function that initializes the network structure (its variables) with
    # the trained values contained in the checkpoint
    init_fn = slim.assign_from_checkpoint_fn(model_path, slim.get_model_variables())

    session_config = tf.ConfigProto(allow_soft_placement=True)

    session_config.gpu_options.per_process_gpu_memory_fraction = gpu_memory_fraction

    with tf.Session(config=session_config) as sess:
        init_fn(sess)

        for image_path in image_paths:
            image_string = tf.gfile.FastGFile(image_path, 'rb').read()
            predictions = sess.run(probabilities, {input_image_t: image_string})
            print(np.array_str(predictions, precision=2, suppress_small=True)
                  + ': ' + path.basename(image_path))