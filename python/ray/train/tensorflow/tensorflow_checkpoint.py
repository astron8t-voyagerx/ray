import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import tensorflow as tf
from tensorflow import keras

from ray.train._internal.framework_checkpoint import FrameworkCheckpoint
from ray.util.annotations import PublicAPI

if TYPE_CHECKING:
    from ray.data.preprocessor import Preprocessor


@PublicAPI(stability="beta")
class TensorflowCheckpoint(FrameworkCheckpoint):
    """A :py:class:`~ray.train.Checkpoint` with TensorFlow-specific functionality."""

    MODEL_FILENAME_KEY = "_model_filename"

    @classmethod
    def from_model(
        cls,
        model: keras.Model,
        *,
        preprocessor: Optional["Preprocessor"] = None,
    ) -> "TensorflowCheckpoint":
        """Create a :py:class:`~ray.train.Checkpoint` that stores a Keras model.

        The checkpoint created with this method needs to be paired with
        `model` when used.

        Args:
            model: The Keras model, whose weights are stored in the checkpoint.
            preprocessor: A fitted preprocessor to be applied before inference.

        Returns:
            A :py:class:`TensorflowCheckpoint` containing the specified model.

        Examples:

            .. testcode::

                from ray.train.tensorflow import TensorflowCheckpoint
                import tensorflow as tf

                model = tf.keras.applications.resnet.ResNet101()
                checkpoint = TensorflowCheckpoint.from_model(model)

            .. testoutput::
                :options: +MOCK
                :hide:

                ...  # Model may or may not be downloaded

        """
        tempdir = tempfile.mkdtemp()
        filename = "model.keras"
        model.save(Path(tempdir, filename).as_posix())

        checkpoint = cls.from_directory(tempdir)
        if preprocessor:
            checkpoint.set_preprocessor(preprocessor)
        checkpoint.update_metadata({cls.MODEL_FILENAME_KEY: filename})
        return checkpoint

    @classmethod
    def from_h5(
        cls, file_path: str, *, preprocessor: Optional["Preprocessor"] = None
    ) -> "TensorflowCheckpoint":
        """Create a :py:class:`~ray.train.Checkpoint` that stores a Keras
        model from H5 format.

        The checkpoint generated by this method contains all the information needed.
        Thus no `model` is needed to be supplied when using this checkpoint.

        Args:
            file_path: The path to the .h5 file to load model from. This is the
                same path that is used for ``model.save(path)``.
            preprocessor: A fitted preprocessor to be applied before inference.

        Returns:
            A :py:class:`TensorflowCheckpoint` converted from h5 format.

        """
        if not os.path.isfile(file_path) or not file_path.endswith(".h5"):
            raise ValueError(
                "Please supply a h5 file path to `TensorflowCheckpoint.from_h5()`."
            )
        tempdir = tempfile.mkdtemp()
        filename = os.path.basename(file_path)
        new_checkpoint_file = Path(tempdir, filename).as_posix()
        shutil.copy(file_path, new_checkpoint_file)

        checkpoint = cls.from_directory(tempdir)
        if preprocessor:
            checkpoint.set_preprocessor(preprocessor)
        checkpoint.update_metadata({cls.MODEL_FILENAME_KEY: filename})
        return checkpoint

    @classmethod
    def from_saved_model(
        cls, dir_path: str, *, preprocessor: Optional["Preprocessor"] = None
    ) -> "TensorflowCheckpoint":
        """Create a :py:class:`~ray.train.Checkpoint` that stores a Keras
        model from SavedModel format.

        The checkpoint generated by this method contains all the information needed.
        Thus no `model` is needed to be supplied when using this checkpoint.

        Args:
            dir_path: The directory containing the saved model. This is the same
                directory as used by ``model.save(dir_path)``.
            preprocessor: A fitted preprocessor to be applied before inference.

        Returns:
            A :py:class:`TensorflowCheckpoint` converted from SavedModel format.

        """
        if not os.path.isdir(dir_path):
            raise ValueError(
                "Please supply a directory to `TensorflowCheckpoint.from_saved_model`"
            )
        tempdir = tempfile.mkdtemp()
        # TODO(ml-team): Replace this with copytree()
        os.rmdir(tempdir)
        shutil.copytree(dir_path, tempdir)

        checkpoint = cls.from_directory(tempdir)
        if preprocessor:
            checkpoint.set_preprocessor(preprocessor)
        # NOTE: The entire directory is the checkpoint.
        checkpoint.update_metadata({cls.MODEL_FILENAME_KEY: "."})
        return checkpoint

    def get_model(
        self,
    ) -> tf.keras.Model:
        """Retrieve the model stored in this checkpoint.

        Returns:
            The Tensorflow Keras model stored in the checkpoint.
        """
        metadata = self.get_metadata()
        if self.MODEL_FILENAME_KEY not in metadata:
            raise ValueError(
                "`TensorflowCheckpoint` cannot retrieve the model if you override the "
                "checkpoint metadata. Please use `Checkpoint.update_metadata` instead."
            )
        model_filename = metadata[self.MODEL_FILENAME_KEY]
        with self.as_directory() as checkpoint_dir:
            model_path = Path(checkpoint_dir, model_filename).as_posix()
            return keras.models.load_model(model_path)
