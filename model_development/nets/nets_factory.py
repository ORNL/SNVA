# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Contains a factory for building various models."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools

import tensorflow as tf

from model_development.nets import resnet_v1
from model_development.nets import alexnet
from model_development.nets import cifarnet
from model_development.nets import densenet_bc
from model_development.nets import inception
from model_development.nets import lenet
from model_development.nets import mobilenet_v1
from model_development.nets import overfeat
from model_development.nets import resnet_v2
from model_development.nets import vgg
from model_development.nets.nasnet import nasnet

slim = tf.contrib.slim

networks_map = {'alexnet_v2': alexnet.alexnet_v2,
                'cifarnet': cifarnet.cifarnet,
                'densenet_bc': densenet_bc.densenet_bc,
                'densenet_bc_12_100': densenet_bc.densenet_bc_12_100,
                'densenet_bc_18_75': densenet_bc.densenet_bc_18_75,
                'densenet_bc_24_50': densenet_bc.densenet_bc_24_50,
                'densenet_bc_12_40': densenet_bc.densenet_bc_12_40,
                'densenet_bc_6_50': densenet_bc.densenet_bc_6_50,
                'inception_v1': inception.inception_v1,
                'inception_v2': inception.inception_v2,
                'inception_v3': inception.inception_v3,
                'inception_v3_025': inception.inception_v3,
                'inception_v4': inception.inception_v4,
                'inception_resnet_v2': inception.inception_resnet_v2,
                'lenet': lenet.lenet,
                'overfeat': overfeat.overfeat,
                'mobilenet_v1': mobilenet_v1.mobilenet_v1,
                'mobilenet_v1_175': mobilenet_v1.mobilenet_v1_175,
                'mobilenet_v1_075': mobilenet_v1.mobilenet_v1_075,
                'mobilenet_v1_050': mobilenet_v1.mobilenet_v1_050,
                'mobilenet_v1_025': mobilenet_v1.mobilenet_v1_025,
                'nasnet_cifar': nasnet.build_nasnet_cifar,
                'nasnet_15_at_1920': nasnet.build_nasnet_15_at_1920,
                'nasnet_7_at_1920': nasnet.build_nasnet_7_at_1920,
                'nasnet_large': nasnet.build_nasnet_large,
                'nasnet_medium': nasnet.build_nasnet_medium,
                'nasnet_mobile': nasnet.build_nasnet_mobile,
                'resnet_v1_50': resnet_v1.resnet_v1_50,
                'resnet_v1_101': resnet_v1.resnet_v1_101,
                'resnet_v1_152': resnet_v1.resnet_v1_152,
                'resnet_v1_200': resnet_v1.resnet_v1_200,
                'resnet_v2_50': resnet_v2.resnet_v2_50,
                'resnet_v2_101': resnet_v2.resnet_v2_101,
                'resnet_v2_152': resnet_v2.resnet_v2_152,
                'resnet_v2_200': resnet_v2.resnet_v2_200,
                'vgg_a': vgg.vgg_a,
                'vgg_16': vgg.vgg_16,
                'vgg_19': vgg.vgg_19
                }

arg_scopes_map = {'alexnet_v2': alexnet.alexnet_v2_arg_scope,
                  'cifarnet': cifarnet.cifarnet_arg_scope,
                  'densenet_bc': densenet_bc.densenet_arg_scope,
                  'densenet_bc_12_100': densenet_bc.densenet_arg_scope,
                  'densenet_bc_18_75': densenet_bc.densenet_arg_scope,
                  'densenet_bc_24_50': densenet_bc.densenet_arg_scope,
                  'densenet_bc_12_40': densenet_bc.densenet_arg_scope,
                  'densenet_bc_6_50': densenet_bc.densenet_arg_scope,
                  'inception_v1': inception.inception_v3_arg_scope,
                  'inception_v2': inception.inception_v3_arg_scope,
                  'inception_v3': inception.inception_v3_arg_scope,
                  'inception_v3_025': inception.inception_v3_arg_scope,
                  'inception_v4': inception.inception_v4_arg_scope,
                  'inception_resnet_v2':
                      inception.inception_resnet_v2_arg_scope,
                  'lenet': lenet.lenet_arg_scope,
                  'mobilenet_v1': mobilenet_v1.mobilenet_v1_arg_scope,
                  'mobilenet_v1_175': mobilenet_v1.mobilenet_v1_arg_scope,
                  'mobilenet_v1_075': mobilenet_v1.mobilenet_v1_arg_scope,
                  'mobilenet_v1_050': mobilenet_v1.mobilenet_v1_arg_scope,
                  'mobilenet_v1_025': mobilenet_v1.mobilenet_v1_arg_scope,
                  'nasnet_cifar': nasnet.nasnet_cifar_arg_scope,
                  'nasnet_15_at_1920': nasnet.nasnet_large_arg_scope,
                  'nasnet_7_at_1920': nasnet.nasnet_large_arg_scope,
                  'nasnet_large': nasnet.nasnet_large_arg_scope,
                  'nasnet_medium': nasnet.nasnet_large_arg_scope,
                  'nasnet_mobile': nasnet.nasnet_mobile_arg_scope,
                  'overfeat': overfeat.overfeat_arg_scope,
                  'resnet_v1_50': resnet_v1.resnet_arg_scope,
                  'resnet_v1_101': resnet_v1.resnet_arg_scope,
                  'resnet_v1_152': resnet_v1.resnet_arg_scope,
                  'resnet_v1_200': resnet_v1.resnet_arg_scope,
                  'resnet_v2_50': resnet_v2.resnet_arg_scope,
                  'resnet_v2_101': resnet_v2.resnet_arg_scope,
                  'resnet_v2_152': resnet_v2.resnet_arg_scope,
                  'resnet_v2_200': resnet_v2.resnet_arg_scope,
                  'vgg_a': vgg.vgg_arg_scope,
                  'vgg_16': vgg.vgg_arg_scope,
                  'vgg_19': vgg.vgg_arg_scope
                  }


def get_network_fn(name,
                   num_classes,
                   weight_decay=0.0,
                   is_training=False,
                   dropout_rate=None):
    """Returns a network_fn such as `logits, end_points = network_fn(images)`.

    Args:
      name: The name of the network.
      num_classes: The number of classes to use for classification.
      weight_decay: The l2 coefficient for the model weights.
      is_training: `True` if the model is being used for training and `False` otherwise.
      dropout_rate: the ratio of activations that are preserved each training step.

    Returns:
      network_fn: A function that applies the model to a batch of images. It has
        the following signature:
          logits, end_points = network_fn(images)
    Raises:
      ValueError: If network `name` is not recognized.
    """
    if name not in networks_map:
        raise ValueError('Name of network unknown %s' % name)
    func = networks_map[name]

    @functools.wraps(func)
    def network_fn(images):
        arg_scope = arg_scopes_map[name](weight_decay=weight_decay)

        with slim.arg_scope(arg_scope):
            if dropout_rate is not None:
                return func(images, num_classes, is_training=is_training, dropout_keep_prob=1-dropout_rate)
            else:
                return func(images, num_classes, is_training=is_training)
    if hasattr(func, 'default_image_size'):
        network_fn.default_image_size = func.default_image_size

    return network_fn
