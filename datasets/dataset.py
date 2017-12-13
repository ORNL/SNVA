# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
r"""Converts washington_street data to TFRecords of TF-Example protos.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datasets import dataset_utils
import math
import os
from os import path
import random
import sys
import tensorflow as tf

slim = tf.contrib.slim


class ImageReader(object):
    """Helper class that provides TensorFlow image coding utilities."""

    def __init__(self):
        # Initializes function that decodes RGB JPEG data.
        self._decode_jpeg_data = tf.placeholder(dtype=tf.string)
        self._decode_jpeg = tf.image.decode_jpeg(self._decode_jpeg_data, channels=3)

    def read_image_dims(self, sess, image_data):
        image = self.decode_jpeg(sess, image_data)
        return image.shape[0], image.shape[1]

    def decode_jpeg(self, sess, image_data):
        image = sess.run(self._decode_jpeg,
                         feed_dict={self._decode_jpeg_data: image_data})
        assert len(image.shape) == 3
        assert image.shape[2] == 3
        return image


def _get_classes(data_subset_dir):
    class_names = []
    
    for filename in os.listdir(data_subset_dir):
        if filename != 'tfrecords':
            if path.isdir(path.join(data_subset_dir, filename)):
                class_names.append(filename)

    return sorted(class_names)
                
                
def _get_filepaths(data_subset_dir, split_name):
    """Returns a list of filepaths and inferred class names.
  
    Args:
      dataset_dir: A directory containing a set of subdirectories representing
        class names. Each subdirectory should contain PNG or JPG encoded images.
  
    Returns:
      A list of image file paths, relative to `dataset_dir` and the list of
      subdirectories, representing class names.
    """
    image_filepaths = []

    # if not eval split, sort before shuffling for repeatability given a random seed
    # if eval split, sort anyway to preserve original frame ordering.
    filenames = sorted(os.listdir(data_subset_dir))

    if split_name != 'eval':
        random.shuffle(filenames)

    for filename in filenames:
        if filename != 'tfrecords':
            filepath = os.path.join(data_subset_dir, filename)
            if os.path.isdir(filepath):
                for imagename in os.listdir(filepath):
                    image_filepath = path.join(filepath, imagename)
                    image_filepaths.append(image_filepath)

    return image_filepaths


def _get_dataset_filename(tfrecords_dir, dataset_name, split_name, shard_id, num_shards):
    output_filename = dataset_name + '_%s_%05d-of-%05d.tfrecord' % (
        split_name, shard_id, num_shards)
    return path.join(tfrecords_dir, output_filename)


def _convert_dataset(dataset_name, split_name, filepaths, class_names_to_ids, tfrecords_dir,
                     batch_size, num_shards):
    """Converts the given filepaths to a TFRecord dataset.
  
    Args:
      split_name: The name of the data subset; either 'training', 'dev', 'test' or 'eval'.
      filepaths: A list of absolute paths to png or jpg images.
      class_names_to_ids: A dictionary from class names (strings) to ids
        (integers).
      tfrecords_dir: The directory where the converted datasets are stored.
    """
    if not path.exists(path.join(path.join(tfrecords_dir, '..'), split_name)):
        raise AssertionError()

    filepaths_len = len(filepaths)

    with tf.Graph().as_default():
        image_reader = ImageReader()

        with tf.Session('') as sess:
            for shard_id in range(num_shards):
                output_filename = _get_dataset_filename(
                    tfrecords_dir, dataset_name, split_name, shard_id, num_shards)

                with tf.python_io.TFRecordWriter(output_filename) as tfrecord_writer:
                    start_ndx = shard_id * batch_size
                    end_ndx = min((shard_id + 1) * batch_size, filepaths_len)
                    for i in range(start_ndx, end_ndx):
                        sys.stdout.write('\r>> Converting image %d/%d shard %d' % (i + 1, filepaths_len, shard_id))
                        sys.stdout.flush()

                        # Read the filename:
                        print(filepaths[i])
                        image_data = tf.gfile.FastGFile(filepaths[i], 'rb').read()
                        height, width = image_reader.read_image_dims(sess, image_data)

                        class_name = path.basename(path.dirname(filepaths[i]))
                        class_id = class_names_to_ids[class_name]

                        example = dataset_utils.image_to_tfexample(image_data, b'jpg', height, width, class_id)
                        tfrecord_writer.write(example.SerializeToString())

    sys.stdout.write('\n')
    sys.stdout.flush()


def _dataset_exists(dataset_name, tfrecords_dir, splits_to_shards):
    """Returns false if a named file does not exist or if the number of
    shards to be written is not equal to the number of shards that exists.
  
    Args:
      dataset_name: The name of the dataset.
      tfrecords_dir: The full path to the directory containing TFRecord shards.
      splits_to_shards: a map from split names (e.g. 'training') to a number of shards
    """
    for split_name, num_shards in splits_to_shards.items():
        for shard_id in range(num_shards):
            output_filename = _get_dataset_filename(
                tfrecords_dir, dataset_name, split_name, shard_id, num_shards)

            if not tf.gfile.Exists(output_filename):
                return False
    return True


def get_split(dataset_name, split_name, datasets_root_dir, file_pattern=None, reader=None):
    """Gets a dataset tuple with instructions for reading construction.
  
    Args:
      split_name: A training/dev split name.
      dataset_dir: The base directory of the dataset sources.
      file_pattern: The file pattern to use when matching the dataset sources.
        It is assumed that the pattern contains a '%s' string so that the split
        name can be inserted.
      reader: The TensorFlow reader type.
  
    Returns:
      A `Dataset` namedtuple.
  
    Raises:
      ValueError: if `split_name` is not a valid training/dev split.
    """
    dataset_dir = path.join(datasets_root_dir, dataset_name)
    tfrecords_dir = path.join(dataset_dir, 'tfrecords')

    splits_filename = dataset_name + '_splits.txt'

    if dataset_utils.has_splits(tfrecords_dir, splits_filename):
        splits_to_sizes = dataset_utils.read_split_file(tfrecords_dir, splits_filename)
    else:
        raise ValueError(path.join(tfrecords_dir, splits_filename) + ' does not exist')

    if split_name not in splits_to_sizes:
        raise ValueError('split name %s was not recognized.' % split_name)

    if not file_pattern:
        file_pattern = dataset_name + '_%s_*.tfrecord'
    file_pattern = path.join(tfrecords_dir, file_pattern % split_name)

    # Allowing None in the signature so that dataset_factory can use the default.
    if reader is None:
        reader = tf.TFRecordReader

    keys_to_features = {
        'image/encoded': tf.FixedLenFeature((), tf.string, default_value=''),
        'image/format': tf.FixedLenFeature((), tf.string, default_value='png'),
        'image/class/label': tf.FixedLenFeature(
            [], tf.int64, default_value=tf.zeros([], dtype=tf.int64)),
    }

    items_to_handlers = {
        'image': slim.tfexample_decoder.Image(),
        'label': slim.tfexample_decoder.Tensor('image/class/label'),
    }

    decoder = slim.tfexample_decoder.TFExampleDecoder(
        keys_to_features, items_to_handlers)

    labels_filename = dataset_name + '_labels.txt'
    labels_to_names = None
    if dataset_utils.has_labels(tfrecords_dir, labels_filename):
        labels_to_names = dataset_utils.read_label_file(tfrecords_dir, labels_filename)

    descriptions_filename = dataset_name + '_descriptions.txt'
    items_to_descriptions = None
    if dataset_utils.has_descriptions(tfrecords_dir, descriptions_filename):
        items_to_descriptions = dataset_utils.read_description_file(tfrecords_dir, descriptions_filename)

    return slim.dataset.Dataset(
        data_sources=file_pattern,
        reader=reader,
        decoder=decoder,
        num_samples=splits_to_sizes[split_name],
        items_to_descriptions=items_to_descriptions,
        num_classes=len(labels_to_names),
        labels_to_names=labels_to_names)


def convert(datasets_root_dir, dataset_name, batch_size, random_seed, split_names):
    """Runs the download and conversion operation.

    Args:
      datasets_root_dir: The directory where all datasets are stored.
      dataset_name: The the subfolder where the named dataset's TFRecords are stored.
      batch_size: The number of shards per batch of TFRecords.
      random_seed: The random seed used to instantiate the pseudo-random number generator
      that shuffles non-eval samples before creating TFRecord shards
      convert_eval_subset: If True, assume an subdir named 'eval' exists in datasets_root_dir
      and create TFRecords for the samples in that directory.
    """
    
    dataset_dir = path.join(datasets_root_dir, dataset_name)

    if not tf.gfile.Exists(dataset_dir):
        raise ValueError('The dataset ' + dataset_name + ' either does not exist or is misnamed')

    random.seed(random_seed)

    splits_to_filepaths = {}
    splits_to_sizes = {}
    splits_to_shards = {}

    class_path = path.join(dataset_dir, split_names[0])

    if not path.exists(class_path):
        os.mkdir(class_path)

    class_names = _get_classes(class_path)

    for split_name in split_names:
        split_dir = path.join(dataset_dir, split_name)
        image_filepaths = _get_filepaths(split_dir, split_name)
        num_samples = len(image_filepaths)

        splits_to_filepaths[split_name] = image_filepaths
        splits_to_sizes[split_name] = num_samples
        splits_to_shards[split_name] = int(math.ceil(num_samples / batch_size))

    tfrecords_dir = path.join(dataset_dir, 'tfrecords')

    if tf.gfile.Exists(tfrecords_dir):
        if _dataset_exists(dataset_name, tfrecords_dir, splits_to_shards):
            print('Dataset files already exist. Exiting without re-creating them.')
            return
        else:
            for file in os.listdir(tfrecords_dir):
                os.remove(path.join(tfrecords_dir, file))
    else:
        tf.gfile.MakeDirs(tfrecords_dir)

    class_name_enum = [class_name for class_name in enumerate(class_names)]

    class_names_to_ids = {class_name: ndx for (ndx, class_name) in class_name_enum}

    # First, convert the traininging and dev sets.
    for split_name in split_names:
        _convert_dataset(dataset_name, split_name, splits_to_filepaths[split_name], class_names_to_ids,
                         tfrecords_dir, batch_size, splits_to_shards[split_name])

    # Then, write the labels file:
    labels_filename = dataset_name + '_labels.txt'
    labels_to_class_names = {ndx: class_name for (ndx, class_name) in class_name_enum}
    dataset_utils.write_label_file(labels_to_class_names, tfrecords_dir, labels_filename)

    # Then, write the splits file:
    splits_filename = dataset_name + '_splits.txt'
    # splits_to_sizes = {'training': num_traininging_samples, 'dev': num_dev_samples}
    dataset_utils.write_split_file(splits_to_sizes, tfrecords_dir, splits_filename)

    # Finally, write the descriptions file:
    descriptions_filename = dataset_name + '_descriptions.txt'
    items_to_descriptions = {'image': 'A color image of varying size.',
                             'label': 'A single integer between 0 and 1'}
    dataset_utils.write_description_file(items_to_descriptions, tfrecords_dir, descriptions_filename)

    # _clean_up_temporary_files(tfrecords_dir)
    print('\nFinished converting the ' + dataset_name + ' dataset!')
