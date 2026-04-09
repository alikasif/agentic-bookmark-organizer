const path = require('path');
const fs = require('fs');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
  entry: {
    'service-worker': './src/background/service-worker.ts',
    popup: './src/popup/popup.ts',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
    clean: true,
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js'],
  },
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        {
          from: 'src/popup/popup.html',
          to: 'popup.html',
        },
        {
          from: 'src/popup/popup.css',
          to: 'popup.css',
        },
      ],
    }),
  ],
  mode: 'production',
};
