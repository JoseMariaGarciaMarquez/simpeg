import numpy as np
import properties
from six import integer_types
import warnings

from .survey import BaseSurvey
from .utils import mkvc

__all__ = ['Data', 'SyntheticData']


class UncertaintyArray(properties.Array):

    class_info = "An array that can be set by a scalar value or numpy array"

    def validate(self, instance, value):
        if isinstance(value, integer_types):
            return float(value)
        elif isinstance(value, float):
            return value
        return super(properties.Array, self).validate(instance, value)


class Data(properties.HasProperties):
    """
    Data storage. This class keeps track of observed data, standard deviation
    of those data and the noise floor.
    """

    dobs = properties.Array(
        """
        Vector of the observed data. The data can be set using the survey
        parameters:

        .. code:: python
            data = Data(survey)
            for src in survey.srcList:
                for rx in src.rxList:
                    index = data.index_dict[src][rx]
                    data.dobs[index] = datum

        """,
        shape=('*',), required=True
    )

    standard_deviation = UncertaintyArray(
        """
        Standard deviation of the data. This can be set using an array of the
        same size as the data (e.g. if you want to assign a different standard
        deviation to each datum) or as a scalar if you would like to assign a
        the same standard deviation to all data.

        For example, if you set

        .. code:: python
            data = Data(survey, dobs=dobs)
            data.standard_deviation = 0.05

        then the contribution to the uncertainty is equal to

        .. code:: python
            data.standard_deviation * np.abs(data.dobs)

        """,
        shape=('*',)
    )

    noise_floor = UncertaintyArray(
        """
        Noise floor of the data. This can be set using an array of the
        same size as the data (e.g. if you want to assign a different noise
        floor to each datum) or as a scalar if you would like to assign a
        the same noise floor to all data.

        For example, if you set

        .. code:: python
            data = Data(survey, dobs=dobs)
            data.noise_floor = 1e-10

        then the contribution to the uncertainty is equal to

        .. code:: python
            data.noise_floor

        """,
        shape=('*',)
    )

    survey = properties.Instance(
        "a SimPEG survey object", BaseSurvey, required=True
    )

    _uid = properties.Uuid("unique ID for the data")

    #######################
    # Instantiate the class
    #######################
    def __init__(
        self, survey, dobs=None, standard_deviation=None, noise_floor=None
    ):
        super(Data, self).__init__()
        self.survey = survey

        # Observed data
        if dobs is None:
            dobs = np.nan*np.ones(survey.nD)  # initialize data as nans
        self.dobs = dobs

        # Standard deviation (initialize as zero)
        if standard_deviation is None:
            standard_deviation = np.zeros(survey.nD)
        self.standard_deviation = standard_deviation

        # Noise floor (initialize as zero)
        if noise_floor is None:
            noise_floor = np.zeros(survey.nD)
        self.noise_floor = noise_floor

    #######################
    # Properties
    #######################
    @property
    def uncertainty(self):
        """
        Data uncertainties. If a stardard deviation and noise floor are
        provided, the incertainty is

        ..code:: python

            data.uncertainty == (
                data.standard_deviation * np.absolute(data.dobs) +
                data.noise_floor
            )

        otherwise, the uncertainty can be set directly

        ..code:: python

            data.uncertainty = 0.05 * np.absolute(self.dobs) + 1e-12

        Note that setting the uncertainty directly will clear the :code:`standard_deviation`
        and set the value to the `noise_floor` property.

        """
        if self.standard_deviation is None and self.noise_floor is None:
            raise Exception(
                "The standard_deviation and / or noise_floor must be set "
                "before asking for uncertainties. Alternatively, the "
                "uncertainty can be set directly"
            )

        uncert = np.zeros(self.nD)
        if self.standard_deviation is not None:
            uncert = uncert + self.standard_deviation * np.absolute(self.dobs)
        if self.noise_floor is not None:
            uncert = uncert + self.noise_floor

        return uncert

    @uncertainty.setter
    def uncertainty(self, value):
        self.self.standard_deviation = np.zeros(self.nD)
        self.noise_floor = value

    @property
    def nD(self):
        return len(self.dobs)

    ##########################
    # Observers and validators
    ##########################

    @properties.validator('dobs')
    def _dobs_validator(self, change):
        if self.survey.nD != len(change['value']):
            raise ValueError(
                "{} must have the same length as the number of data. The "
                "provided input has len {}, while the survey expects "
                "survey.nD = {}".format(
                    change["name"], len(change["value"]), self.survey.nD
                )
            )

    @properties.validator(['standard_deviation', 'noise_floor'])
    def _uncertainty_validator(self, change):
        if isinstance(change['value'], float):
            change['value'] = change['value'] * np.ones(self.nD)
        self._dobs_validator(change)


    @property
    def index_dict(self):
        """
        Dictionary of data indices by sources and receivers. To set data using
        survey parameters:

        .. code::
            data = Data(survey)
            for src in survey.srcList:
                for rx in src.rxList:
                    index = data.index_dict[src][rx]
                    data.dobs[index] = datum

        """
        if getattr(self, '_index_dict', None) is None:
            if self.survey is None:
                raise Exception(
                    "To set or get values by source-receiver pairs, a survey must "
                    "first be set. `data.survey = survey`"
                )

            # create an empty dict
            self._index_dict = {}

            # create an empty dict associated with each source
            for src in self.survey.source_list:
                self._index_dict[src] = {}

            # loop over sources and find the associated data indices
            indBot, indTop = 0, 0
            for src in self.survey.source_list:
                for rx in src.receiver_list:
                    indTop += rx.nD
                    self._index_dict[src][rx] = np.arange(indBot, indTop)
                    indBot += rx.nD

        return self._index_dict

    ##########################
    # Depreciated
    ##########################
    @property
    def std(self):
        warnings.warn(
            "std has been depreciated in favor of standard_deviation. Please "
            "update your code to use 'standard_deviation'"
        )
        return self.standard_deviation

    @std.setter
    def std(self, value):
        warnings.warn(
            "std has been depreciated in favor of standard_deviation. Please "
            "update your code to use 'standard_deviation'"
        )
        self.standard_deviation = value

    @property
    def eps(self):
        warnings.warn(
            "eps has been depreciated in favor of noise_floor. Please "
            "update your code to use 'noise_floor'"
        )
        return self.noise_floor

    @eps.setter
    def eps(self, value):
        warnings.warn(
            "eps has been depreciated in favor of noise_floor. Please "
            "update your code to use 'noise_floor'"
        )
        self.noise_floor = value

    def __setitem__(self, key, value):
        warnings.warn(
            """
            Treating the data object as a dictionary has been depreciated in
            in favor of working with the index_dict. Please update your code to
            use

            .. code::

                index = data.index_dict[src][rx]
                data.dobs[index] = datum

            """
        )
        index = self.index_dict[key[0]][key[1]]
        self.dobs[index] = value

    def __getitem__(self, key):
        warnings.warn(
            """
            Treating the data object as a dictionary has been depreciated in
            in favor of working with the index_dict. Please update your code to
            use

            .. code::

                index = data.index_dict[src][rx]
                datum = data.dobs[index]

            """
        )
        index = self.index_dict[key[0]][key[1]]
        return self.dobs[index]

    def tovec(self):
        warnings.warn(
            """
            data.tovec is no longer necessary. Please update your code to call
            data.dobs directly.
            """
        )
        return self.dobs

    def fromvec(self, v):
        raise Exception(
            "fromvec has been depreciated. Please use the index_dict to "
            "interact with the data as a dictionary"
        )

class SyntheticData(Data):
    """
    Data class for synthetic data. It keeps track of observed and clean data
    """

    dclean = properties.Array(
        """
        Vector of the clean synthetic data. The data can be set using the survey
        parameters:

        .. code:: python
            data = Data(survey)
            for src in survey.srcList:
                for rx in src.rxList:
                    index = data.inices_by_survey(src, rx)
                    data.dclean[indices] = datum

        """,
        shape=('*',), required=True
    )

    def __init__(
        self, survey, dobs=None, dclean=None, standard_deviation=None,
        noise_floor=None
    ):
        super(SyntheticData, self).__init__(
            survey=survey, dobs=dobs,
            standard_deviation=standard_deviation, noise_floor=noise_floor
        )

        if dclean is None:
            dclean = np.nan*np.ones(self.survey.nD)
        self.dclean = dclean

    @properties.validator('dclean')
    def _dclean_validator(self, change):
        self._dobs_validator(change)
