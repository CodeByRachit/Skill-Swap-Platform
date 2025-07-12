const PORT = process.env.PORT || 5000;
mongoose.connect(process.env.MONGO_URI).then(() => {
  app.listen(PORT, () => console.log(`Backend running on port ${PORT}`));
});
