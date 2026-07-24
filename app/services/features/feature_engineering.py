class FeatureEngineering:

    @staticmethod
    def calculate_fragmentation(
        apps: list[str]
    ):

        if len(apps) <= 1:
            return 0

        switches = 0

        for i in range(1, len(apps)):
            if apps[i] != apps[i - 1]:
                switches += 1

        return switches / (len(apps) - 1)