# -*- coding: utf-8 -*-
"""This script provides command line access for testing forecasters on
custom data sets.

Example:
    $python deep4cast.py --data-path "./tutorials/timeseries_data.csv"
    # --lag 20 --test-fraction 0.1

"""
import argparse

import numpy as np
from pandas import read_table

from deep4cast.forecasters import Forecaster
from deep4cast.metrics import adjust_for_horizon, mape


def main(args):
    """Main function that handles forecasting given list of arugments."""
    # Load training at test data from file input
    print("\n\nLoading datasets.")
    df = read_table(args.data_path, sep=',')
    ts = df.values

    # Format data to shape (n_steps, n_vars, n_series)
    while len(ts.shape) < 3:
        ts = np.expand_dims(ts, axis=-1)

    # Prepare train and test set. Make sure to catch the case when the user
    # did not supply a test. We use the end of the time series for testing
    # because of lookahead bias.
    if args.test_fraction:
        test_length = int(len(df) * args.test_fraction)
        train_length = len(df) - test_length
        ts_train = ts[:-test_length]
        ts_test = ts[-test_length - args.lag:]
    else:
        ts_train = ts

    topology = [
        {
            'meta': {
                'layer_type': 'Conv1D',
                'layer_id': 'c1',
                'parent_ids': ['input']
            },
            'params': {
                'filters': 64,
                'kernel_size': 5,
                'activation': 'elu'
            }
        },
        {
            'meta': {
                'layer_type': 'Conv1D',
                'layer_id': 'c2',
                'parent_ids': ['c1']
            },
            'params': {
                'filters': 64,
                'kernel_size': 3,
                'activation': 'elu'
            }
        },
        {
            'meta': {
                'layer_type': 'Conv1D',
                'layer_id': 'c3',
                'parent_ids': ['c2']
            },
            'params': {
                'filters': 128,
                'kernel_size': 3,
                'activation': 'elu'
            }
        },
        {
            'meta': {
                'layer_type': 'Flatten',
                'layer_id': 'f1',
                'parent_ids': ['c3']
            },
            'params': {}
        },
        {
            'meta': {
                'layer_type': 'Dense',
                'layer_id': 'd1',
                'parent_ids': ['f1']
            },
            'params': {
                'units': 128,
                'activation': 'elu'
            }
        },
        {
            'meta': {
                'layer_type': 'Dense',
                'layer_id': 'd2',
                'parent_ids': ['d1']
            },
            'params': {
                'units': 128,
                'activation': 'elu'
            }
        }
    ]

    forecaster = Forecaster(
        topology,
        optimizer='sgd',
        lag=args.lag,
        horizon=args.horizon,
        batch_size=args.batch_size,
        epochs=args.epochs,
        uncertainty=args.uncertainty,
        dropout_rate=args.dropout_rate,
        lr=args.learning_rate
    )
    forecaster.fit(ts_train)

    # Print errors to screen using a specified metric function
    metric = adjust_for_horizon(mape)
    ts_train_pred = forecaster.predict(
        ts_train, n_samples=args.n_samples
    )['mean']
    if args.test_fraction:
        ts_test_pred = forecaster.predict(
            ts_test, n_samples=args.n_samples
        )['mean']
        print(
            'TRAIN \t Mean Absolute Percentage Error: {0:.1f}%'.format(
                metric(
                    ts_train_pred,
                    ts[args.lag:train_length]
                )
            )
        )
        print(
            'TEST \t Mean Absolute Percentage Error: {0:.1f}%'.format(
                metric(ts_test_pred, ts[train_length:])
            )
        )
    else:
        print(
            'TRAIN \t Mean Absolute Percentage Error: {0:.1f}%'.format(
                metric(ts_train_pred, ts[args.lag:])
            )
        )


def _get_parser():
    # Collect all relevant command line arguments
    parser = argparse.ArgumentParser()
    named_args = parser.add_argument_group('named arguments')

    named_args.add_argument('-d', '--data-path',
                            help="Location of data set",
                            required=True,
                            type=str)

    named_args.add_argument('-tf', '--test-fraction',
                            help="Test fraction at end of dataset",
                            required=False,
                            default=None,
                            type=float)

    named_args.add_argument('-lg', '--lag',
                            help="Lookback period",
                            required=True,
                            type=int)

    named_args.add_argument('-hr', '--horizon',
                            help="Forecasting horizon",
                            required=False,
                            default=1,
                            type=int)

    named_args.add_argument('-e', '--epochs',
                            help="Number of epochs to run",
                            required=False,
                            default=100,
                            type=int)

    named_args.add_argument('-b', '--batch-size',
                            help="Number of training batches",
                            required=False,
                            default=8,
                            type=int)

    named_args.add_argument('-u', '--uncertainty',
                            help="Toggle uncertainty",
                            required=False,
                            default=False,
                            type=bool)

    named_args.add_argument('-dr', '--dropout_rate',
                            help="Dropout rate",
                            required=False,
                            default=0.1,
                            type=float)

    named_args.add_argument('-s', '--n_samples',
                            help="Number of dropout samples",
                            required=False,
                            default=10,
                            type=int)

    named_args.add_argument('-lr', '--learning-rate',
                            help="Learning rate",
                            required=False,
                            default=0.1,
                            type=float)

    return parser


if __name__ == '__main__':
    args = _get_parser().parse_args()
    main(args)
