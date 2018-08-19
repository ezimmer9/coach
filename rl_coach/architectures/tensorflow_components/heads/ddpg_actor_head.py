#
# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import tensorflow as tf

from rl_coach.architectures.tensorflow_components.architecture import batchnorm_activation_dropout
from rl_coach.architectures.tensorflow_components.heads.head import Head, HeadParameters
from rl_coach.base_parameters import AgentParameters
from rl_coach.core_types import ActionProbabilities
from rl_coach.spaces import SpacesDefinition


class DDPGActorHeadParameters(HeadParameters):
    def __init__(self, activation_function: str ='tanh', name: str='policy_head_params', batchnorm: bool=True):
        super().__init__(parameterized_class=DDPGActor, activation_function=activation_function, name=name)
        self.batchnorm = batchnorm


class DDPGActor(Head):
    def __init__(self, agent_parameters: AgentParameters, spaces: SpacesDefinition, network_name: str,
                 head_idx: int = 0, loss_weight: float = 1., is_local: bool = True, activation_function: str='tanh',
                 batchnorm: bool=True):
        super().__init__(agent_parameters, spaces, network_name, head_idx, loss_weight, is_local, activation_function)
        self.name = 'ddpg_actor_head'
        self.return_type = ActionProbabilities

        self.num_actions = self.spaces.action.shape

        self.batchnorm = batchnorm

        # bounded actions
        self.output_scale = self.spaces.action.max_abs_range

        # a scalar weight that penalizes high activation values (before the activation function) for the final layer
        if hasattr(agent_parameters.algorithm, 'action_penalty'):
            self.action_penalty = agent_parameters.algorithm.action_penalty

    def _build_module(self, input_layer):
        # mean
        pre_activation_policy_values_mean = tf.layers.dense(input_layer, self.num_actions, name='fc_mean')
        policy_values_mean = batchnorm_activation_dropout(pre_activation_policy_values_mean, self.batchnorm,
                                                          self.activation_function,
                                                          False, 0, 0)[-1]
        self.policy_mean = tf.multiply(policy_values_mean, self.output_scale, name='output_mean')

        if self.is_local:
            # add a squared penalty on the squared pre-activation features of the action
            if self.action_penalty and self.action_penalty != 0:
                self.regularizations += \
                    [self.action_penalty * tf.reduce_mean(tf.square(pre_activation_policy_values_mean))]

        self.output = [self.policy_mean]
