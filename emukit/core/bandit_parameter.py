# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


from typing import Union, Tuple, List, Any, Optional

import numpy as np

from .parameter import Parameter
from .continuous_parameter import ContinuousParameter
from .categorical_parameter import CategoricalParameter
from .discrete_parameter import DiscreteParameter
from .encodings import OneHotEncoding

class BanditParameter(Parameter):
    """
    A multivariate parameter consisting of a restricted domain of the full Cartesian product of its
    constituent sub-parameters
    """
    def __init__(self, name: str, domain: np.ndarray, sub_parameter_names: Optional[List[str]]=None):
        """
        :param name: Name of parameter
        :param domain: List of tuples representing valid values
        :param parameters: List of parameters, must correspond to domain if provided, otherwise will
        be reflected from the domain
        """
        self.name = name
        assert isinstance(domain, np.ndarray)
        assert domain.ndim==2
        self.domain = domain  # each column is homogeneously typed thanks to numpy.ndarray
        self.parameters = self._create_parameters(domain, sub_parameter_names)

    def _create_parameter_names(self, domain: np.ndarray) -> List[str]:
        return [f'{self.name}_{i}' for i in range(domain.shape[1])]

    def _create_parameters(self, domain: np.ndarray, parameter_names: Optional[List[str]]) -> List[Parameter]:
        """ Reflect parameters from domain.
        """
        parameters = []
        parameter_names = parameter_names if parameter_names else self._create_parameter_names(domain)
        assert domain.shape[1] == len(parameter_names)
        for cix, parameter_name in enumerate(parameter_names):
            sub_param_domain = domain[:,cix]
            domain_unq = np.unique(sub_param_domain)
            if np.issubdtype(sub_param_domain.dtype, np.number):  # make discrete
                parameter = DiscreteParameter(name = parameter_name, domain = domain_unq)
            else:  # make categorical
                encoding = OneHotEncoding(domain_unq)
                parameter = CategoricalParameter(name = parameter_name, encoding = encoding)
                raise NotImplementedError("Categorical sub-parameters not yet fully supported")
            parameters.append(parameter)
        return(parameters)

    def check_in_domain(self, x: Union[np.ndarray, float]) -> bool:
        """
        Checks if all the points in x lie in the domain set

        :param x:    1d numpy array of points to check
                  or 2d numpy array with shape (n_points, 1) of points to check
                  or float of single point to check
        :return: A boolean value which indicates whether all points lie in the domain
        """
        if isinstance(x, np.ndarray):
            if x.ndim == 2 and x.shape[1] == 1:
                x = x.ravel()
            elif x.ndim > 1:
                raise ValueError("Expected x shape (n,) or (n, 1), actual is {}".format(x.shape))
        return (self.domain == x).all(axis=1).any()

    @property
    def bounds(self) -> List[Tuple]:
        """
        Returns a list containing the bounds for each constituent parameter
        """
        return [pb for p in self.parameters for pb in p.bounds]

    def round(self, x: np.ndarray) -> np.ndarray:
        """
        Rounds each row in x to represent a valid value for this bandit variable. Note that this
        valid value may be 'far' from the suggested value.

        :param x: A 2d array NxD to be rounded (D is len(self.parameters))
        :returns: An array NxD where each row represents a value from the domain
                  that is closest to the corresponding row in x
        """
        if x.ndim != 2:
            raise ValueError("Expected 2d array, got " + str(x.ndim))

        if x.shape[1] != self.dimension:
            raise ValueError("Expected {} column array, got {}".format(self.dimension, x.shape[1]))

        x_rounded = []
        for row in x:
            dists = np.sqrt(np.sum((self.domain - row)**2))
            rounded_value = min(self.domain, key=lambda d: np.linalg.norm(d-row))
            x_rounded.append([rounded_value])

        assert all([self.check_in_domain(xr) for xr in x_rounded])
        return np.row_stack(x_rounded)

    @property
    def dimension(self) -> int:
        d = 0
        for p in self.parameters:
            if isinstance(p, ContinuousParameter): d+=1
            elif isinstance(p, DiscreteParameter): d+=1
            elif isinstance(p, CategoricalParameter): d+=p.dimension
            else: raise Exception("Parameter type {type(p)} not supported.")
        return d


    def sample_uniform(self, point_count: int) -> np.ndarray:
        """
        Generates multiple uniformly distributed random parameter points.

        :param point_count: number of data points to generate.
        :returns: Generated points with shape (point_count, num_features)
        """
        return self.domain[np.random.choice(self.domain.shape[0], point_count)]
