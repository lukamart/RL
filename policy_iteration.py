import numpy as np
import tensorflow as tf
import random
from tensorflow import keras
from collections import deque


class PI():
    def __init__(self, hparams, epsilon=1.0, epsilon_min=0.01, epsilon_log_decay=0.995):
        self.hparams = hparams
        np.random.seed(hparams['Rand_Seed'])
        tf.random.set_seed(hparams['Rand_Seed'])
        random.seed(hparams['Rand_Seed'])
        self.policy_network()
        self.memory = deque(maxlen=100000)
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_log_decay

    def policy_network(self):
        self.network = keras.Sequential([
            keras.layers.Dense(self.hparams['hidden_size'], input_dim=self.hparams['input_size'], activation='relu',
                               kernel_initializer=keras.initializers.he_normal(), dtype='float64'),
            keras.layers.Dense(self.hparams['hidden_size'], activation='relu',
                               kernel_initializer=keras.initializers.he_normal(), dtype='float64'),
            keras.layers.Dense(self.hparams['hidden_size'], activation='relu',
                               kernel_initializer=keras.initializers.he_normal(), dtype='float64'),
            keras.layers.Dense(self.hparams['num_actions'], dtype='float64')
        ])
        self.network.compile(loss='mean_squared_error', optimizer=keras.optimizers.Adam(
            epsilon=self.hparams['adam_eps'], learning_rate=self.hparams['learning_rate_adam']))

    def get_action(self, state, env):
        state = self._process_state(state)
        if np.random.random() <= self.hparams['epsilon']:
            selected_action = env.action_space.sample()
        else:
            selected_action = np.argmax(self.network(state))
        return selected_action

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def get_epsilon(self, t):
        return max(self.epsilon_min, min(self.epsilon, 1.0 - np.log10((t + 1) * self.epsilon_decay)))

    def replay(self, batch_size):
        batch = random.sample(self.memory, min(len(self.memory), batch_size))
        states, actions, rewards, new_states, dones = list(map(lambda i: [j[i] for j in batch], range(5)))
        loss = self.update_network(states, actions, rewards, new_states, dones)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        return loss


    def update_network(self, states, actions, rewards, new_states, dones):
        eps_length = len(states)
        states = np.vstack(states)
        y_pred = self.network(states).numpy()
        for i in range(eps_length):
            if dones[i]:
                y_pred[i, actions[i]] = rewards[i]
            else:
                new_state = self._process_state(new_states[i])
                y_pred[i, actions[i]] = rewards[i] + self.hparams['GAMMA'] * tf.math.reduce_max(self.network(new_state)).numpy()
        loss = self.network.train_on_batch(states, y_pred)
        return loss

    def _process_state(self, state):
        return state.reshape([1, self.hparams['input_size']])
